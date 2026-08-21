import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image, ImageOps
import io
from streamlit_cropper import st_cropper

# 支援 iPhone HEIC/HEIF 照片格式
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

st.set_page_config(page_title="我的衣櫥", page_icon="👗", layout="centered")

DB_FILE = "wardrobe.db"
UPLOAD_DIR = "uploaded_clothes"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ----------------- 自定義 CSS（手機最佳化與綠色卡片風格） -----------------
st.markdown("""
<style>
    /* 全域背景 */
    .stApp {
        background-color: #f7f9f7;
    }
    
    /* 頂部數據條 */
    .top-stats {
        display: flex;
        align-items: center;
        gap: 16px;
        font-size: 18px;
        font-weight: 700;
        color: #2b512a;
        margin-bottom: 8px;
    }
    
    /* 均價文字強調 */
    .cpw-price {
        font-size: 22px;
        font-weight: 800;
        color: #1b381b;
        margin-top: 4px;
        margin-bottom: 2px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .sub-info {
        font-size: 14px;
        color: #637863;
        margin-bottom: 10px;
    }

    /* 詳情頁卡片 */
    .detail-box {
        background-color: #ecf6ed;
        border-radius: 16px;
        padding: 16px 18px;
        margin: 12px 0;
        color: #1e3a1e;
    }
    .detail-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        font-size: 15px;
    }
    .season-pill {
        display: inline-block;
        background: #ffffff;
        padding: 5px 14px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        color: #2b512a;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 資料庫操作 -----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS clothes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            wear_count INTEGER DEFAULT 0,
            image_path TEXT,
            created_at TEXT,
            category TEXT DEFAULT '上衣',
            purchase_year TEXT DEFAULT '2026',
            last_worn TEXT DEFAULT '暫無',
            seasons TEXT DEFAULT '全季節'
        )
    ''')
    # 確保升級相容
    c.execute("PRAGMA table_info(clothes)")
    existing_cols = [col[1] for col in c.fetchall()]
    if 'category' not in existing_cols:
        c.execute("ALTER TABLE clothes ADD COLUMN category TEXT DEFAULT '上衣'")
    if 'purchase_year' not in existing_cols:
        c.execute("ALTER TABLE clothes ADD COLUMN purchase_year TEXT DEFAULT '2026'")
    if 'last_worn' not in existing_cols:
        c.execute("ALTER TABLE clothes ADD COLUMN last_worn TEXT DEFAULT '暫無'")
    if 'seasons' not in existing_cols:
        c.execute("ALTER TABLE clothes ADD COLUMN seasons TEXT DEFAULT '全季節'")

    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    defaults = ['上衣', '褲子', '裙子', '外套', '鞋靴', '配件']
    for cat in defaults:
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))
    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM categories ORDER BY id ASC")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

def add_category(cat_name):
    if cat_name.strip():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat_name.strip(),))
        conn.commit()
        conn.close()

def add_clothing(name, price, category, purchase_year, seasons, cropped_image):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    filename = f"{uuid.uuid4().hex}.jpg"
    file_path = os.path.join(UPLOAD_DIR, filename)
    cropped_image.convert('RGB').save(file_path, "JPEG", quality=90)
    
    c.execute(
        '''INSERT INTO clothes (name, price, wear_count, image_path, created_at, category, purchase_year, last_worn, seasons)
           VALUES (?, ?, 0, ?, ?, ?, ?, '暫無', ?)''',
        (name, price, file_path, datetime.now().strftime("%Y-%m-%d"), category, purchase_year, seasons)
    )
    conn.commit()
    conn.close()

def get_clothes(category_filter="全部"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if category_filter == "全部":
        c.execute("SELECT id, name, price, wear_count, image_path, category, purchase_year, last_worn, seasons FROM clothes ORDER BY id DESC")
    else:
        c.execute("SELECT id, name, price, wear_count, image_path, category, purchase_year, last_worn, seasons FROM clothes WHERE category = ? ORDER BY id DESC", (category_filter,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_clothing_by_id(cid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, price, wear_count, image_path, category, purchase_year, last_worn, seasons FROM clothes WHERE id = ?", (cid,))
    row = c.fetchone()
    conn.close()
    return row

def update_wear_count(clothing_id, delta):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    if delta > 0:
        c.execute("UPDATE clothes SET wear_count = wear_count + 1, last_worn = ? WHERE id = ?", (today_str, clothing_id))
    else:
        c.execute("UPDATE clothes SET wear_count = MAX(0, wear_count - 1) WHERE id = ?", (clothing_id,))
    conn.commit()
    conn.close()

def update_clothing_info(cid, name, price, category, year, seasons):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE clothes SET name = ?, price = ?, category = ?, purchase_year = ?, seasons = ? WHERE id = ?",
        (name, price, category, year, seasons, cid)
    )
    conn.commit()
    conn.close()

def delete_clothing(clothing_id, image_path):
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
        except Exception:
            pass
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM clothes WHERE id = ?", (clothing_id,))
    conn.commit()
    conn.close()

init_db()

# 頁面狀態
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

# ==========================================
# 1. 詳情視圖 (點擊查看詳情後顯示)
# ==========================================
if st.session_state.selected_id is not None:
    item = get_clothing_by_id(st.session_state.selected_id)
    if not item:
        st.session_state.selected_id = None
        st.rerun()

    cid, name, price, wear_count, img_path, category, purchase_year, last_worn, seasons = item
    avg_cost = price / wear_count if wear_count > 0 else price

    col_back, _ = st.columns([1, 3])
    with col_back:
        if st.button("⬅ 返回衣櫥", use_container_width=True):
            st.session_state.selected_id = None
            st.rerun()

    st.subheader(f"{name}")

    if os.path.exists(img_path):
        st.image(img_path, use_container_width=True)

    st.markdown(f"""
    <div class="detail-box">
        <div style="font-size: 17px; font-weight: bold; margin-bottom: 8px;">基本信息</div>
        <div class="detail-row"><span>👥 類別</span><span><b>{category}</b></span></div>
        <div class="detail-row"><span>💰 價格</span><span>¥{price:.2f}</span></div>
        <div class="detail-row"><span>🔄 穿著次數</span><span>{wear_count} 次</span></div>
        <div class="detail-row"><span>🕒 上次穿著</span><span>{last_worn}</span></div>
        <div class="detail-row"><span>🏷️ 單次成本</span><span><b>¥{avg_cost:.2f} / 次</b></span></div>
        <div class="detail-row"><span>🛒 購買年份</span><span>{purchase_year}</span></div>
    </div>
    <div class="detail-box">
        <div style="font-size: 17px; font-weight: bold; margin-bottom: 8px;">季節信息</div>
        <div><span class="season-pill">✓ {seasons}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # 快捷打卡與撤銷
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ 今天穿 (+1)", key="dt_add", type="primary", use_container_width=True):
            update_wear_count(cid, 1)
            st.toast("已更新穿著紀錄！")
            st.rerun()
    with c_btn2:
        if st.button("➖ 撤銷 (-1)", key="dt_sub", use_container_width=True, disabled=(wear_count <= 0)):
            update_wear_count(cid, -1)
            st.rerun()

    with st.expander("⚙️ 編輯衣物資料 / 刪除"):
        edit_name = st.text_input("衣服名稱", value=name)
        edit_price = st.number_input("購買原價 (¥)", value=float(price), step=10.0)
        cats = get_categories()
        edit_cat = st.selectbox("分類", cats, index=cats.index(category) if category in cats else 0)
        edit_year = st.text_input("購買年份", value=purchase_year)
        edit_season = st.selectbox("適用季節", ["全季節", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"], index=0)

        e1, e2 = st.columns(2)
        with e1:
            if st.button("💾 儲存修改", use_container_width=True):
                update_clothing_info(cid, edit_name, edit_price, edit_cat, edit_year, edit_season)
                st.success("已更新！")
                st.rerun()
        with e2:
            if st.button("🗑️ 刪除此衣物", type="secondary", use_container_width=True):
                delete_clothing(cid, img_path)
                st.session_state.selected_id = None
                st.rerun()

# ==========================================
# 2. 主列表介面
# ==========================================
else:
    nav_selected = st.segmented_control(
        "導航選單",
        ["🧥 我的衣櫥", "➕ 新增衣服", "🏷️ 分類管理"],
        default="🧥 我的衣櫥",
        label_visibility="collapsed"
    )

    # ===== 分頁：衣櫥清單 =====
    if nav_selected == "🧥 我的衣櫥":
        all_items = get_clothes("全部")
        total_items = len(all_items)
        total_spent = sum(x[2] for x in all_items)

        # 頂部數據看板
        st.markdown(f"""
        <div class="top-stats">
            <span>👕 {total_items} 件</span>
            <span>💰 總投入 ¥{total_spent:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)

        # 頂部分類膠囊 (Pills)
        categories = ["全部"] + get_categories()
        selected_cat = st.pills("分類篩選", categories, default="全部", label_visibility="collapsed")
        
        target_cat = selected_cat if selected_cat else "全部"
        displayed_items = get_clothes(target_cat)

        st.markdown(f"#### {target_cat} ({len(displayed_items)})")

        if not displayed_items:
            st.info("該分類下暫無衣物，請點選「➕ 新增衣服」拍照上傳！")
        else:
            # 手機友善卡片佈局
            for item in displayed_items:
                cid, name, price, wear_count, img_path, cat, p_year, _, _ = item
                avg_cost = price / wear_count if wear_count > 0 else price

                with st.container(border=True):
                    if os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    
                    st.markdown(f"### {name}")
                    st.markdown(f"<div class='cpw-price'>¥{avg_cost:.2f} / 次</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='sub-info'>原價 ¥{price:.0f} &nbsp;|&nbsp; 已穿 {wear_count} 次 &nbsp;|&nbsp; 標籤: {cat}</div>", unsafe_allow_html=True)
                    
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if st.button("🔍 查看詳情", key=f"view_{cid}", use_container_width=True):
                            st.session_state.selected_id = cid
                            st.rerun()
                    with b_col2:
                        if st.button("➕ 今天穿 (+1)", key=f"add_{cid}", type="primary", use_container_width=True):
                            update_wear_count(cid, 1)
                            st.toast(f"已記錄！{name} 穿著次數 +1", icon="👕")
                            st.rerun()

    # ===== 分頁：新增衣服 =====
    elif nav_selected == "➕ 新增衣服":
        st.subheader("新增衣物資料")
        
        item_name = st.text_input("衣物名稱 / 描述", placeholder="例如：條紋寬鬆襯衫")
        
        col1, col2 = st.columns(2)
        with col1:
            item_price = st.number_input("購買價格 (¥)", min_value=0.1, step=10.0, value=149.0)
            avail_cats = get_categories()
            item_cat = st.selectbox("選擇分類", avail_cats)
        with col2:
            item_year = st.text_input("購買年份", value=str(datetime.now().year))
            item_seasons = st.selectbox("適用季節", ["全季節", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"])

        upload_type = st.radio("選擇圖片來源", ["📸 相機拍照", "📁 相簿上傳"], horizontal=True)
        raw_img_bytes = None
        
        if "拍照" in upload_type:
            cam = st.camera_input("拍照")
            if cam:
                raw_img_bytes = cam.getvalue()
        else:
            up = st.file_uploader("選擇照片 (支援 JPG/PNG/HEIC)", type=["jpg", "jpeg", "png", "heic", "heif"])
            if up:
                raw_img_bytes = up.getvalue()

        cropped_img = None
        if raw_img_bytes:
            try:
                st.write("✂️ **拖曳選框裁切衣服區域：**")
                img_obj = Image.open(io.BytesIO(raw_img_bytes))
                img_obj = ImageOps.exif_transpose(img_obj)
                
                cropped_img = st_cropper(
                    img_obj,
                    realtime_update=True,
                    box_color="#34c759",
                    aspect_ratio=None
                )
            except Exception:
                st.error("圖片載入失敗，請確認檔案格式是否正確。")

        if st.button("💾 儲存至衣櫃", type="primary", use_container_width=True):
            if not item_name.strip():
                st.error("請輸入衣服名稱")
            elif cropped_img is None:
                st.error("請上傳並確認衣物照片")
            else:
                add_clothing(item_name.strip(), item_price, item_cat, item_year, item_seasons, cropped_img)
                st.success("✅ 成功加入衣櫃！")
                st.rerun()

    # ===== 分頁：分類管理 =====
    elif nav_selected == "🏷️ 分類管理":
        st.subheader("自定義分類標籤")
        new_c = st.text_input("輸入新分類名稱", placeholder="例如：運動服、居家服、復古款")
        if st.button("➕ 新增分類"):
            if new_c.strip():
                add_category(new_c)
                st.toast(f"已新增分類：{new_c}")
                st.rerun()
        
        st.divider()
        st.write("**目前所有分類標籤：**")
        st.write("、".join([f"`{c}`" for c in get_categories()]))

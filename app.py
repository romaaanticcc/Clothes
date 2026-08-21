import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image
import io
from streamlit_cropper import st_cropper

# 設定頁面配置
st.set_page_config(page_title="衣物詳情與智慧衣櫃", page_icon="👗", layout="centered")

DB_FILE = "wardrobe.db"
UPLOAD_DIR = "uploaded_clothes"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ----------------- 自定義 CSS（還原 UI 卡片樣式） -----------------
st.markdown("""
<style>
    .info-box {
        background-color: #ecf6ed;
        border-radius: 18px;
        padding: 20px 22px;
        margin-top: 15px;
        margin-bottom: 15px;
        color: #1e3a1e;
    }
    .info-title {
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 14px;
        color: #1b381b;
    }
    .info-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 9px 0;
        font-size: 16px;
    }
    .season-chip {
        display: inline-block;
        background-color: #ffffff;
        color: #2b512a;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 15px;
        font-weight: 500;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 資料庫初始化與遷移 -----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 主衣物表
    c.execute('''
        CREATE TABLE IF NOT EXISTS clothes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            wear_count INTEGER DEFAULT 0,
            image_path TEXT,
            created_at TEXT,
            category TEXT DEFAULT '未分類',
            purchase_year TEXT DEFAULT '2026',
            last_worn TEXT DEFAULT '暫無',
            seasons TEXT DEFAULT '全季節'
        )
    ''')
    # 自動補齊舊資料庫欄位
    c.execute("PRAGMA table_info(clothes)")
    existing_cols = [col[1] for col in c.fetchall()]
    if 'category' not in existing_cols:
        c.execute("ALTER TABLE clothes ADD COLUMN category TEXT DEFAULT '未分類'")
    if 'purchase_year' not in existing_cols:
        c.execute("ALTER TABLE clothes ADD COLUMN purchase_year TEXT DEFAULT '2026'")
    if 'last_worn' not in existing_cols:
        c.execute("ALTER TABLE clothes ADD COLUMN last_worn TEXT DEFAULT '暫無'")
    if 'seasons' not in existing_cols:
        c.execute("ALTER TABLE clothes ADD COLUMN seasons TEXT DEFAULT '全季節'")

    # 分類管理表
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    defaults = ['上衣', '褲子', '外套', '洋裝', '鞋靴', '包包配件']
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

# 狀態管理（切換列表與詳情視圖）
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

# ==========================================
# 詳情頁面視圖（依附截圖樣式）
# ==========================================
if st.session_state.selected_id is not None:
    item = get_clothing_by_id(st.session_state.selected_id)
    if not item:
        st.session_state.selected_id = None
        st.rerun()
        
    cid, name, price, wear_count, img_path, category, purchase_year, last_worn, seasons = item
    avg_cost = price / wear_count if wear_count > 0 else price

    # 頂部導覽列
    h_col1, h_col2 = st.columns([6, 1])
    with h_col1:
        if st.button("⬅ 返回衣櫃列表"):
            st.session_state.selected_id = None
            st.rerun()
    st.title("衣物詳情")

    # 1. 衣服大圖展示
    if os.path.exists(img_path):
        st.image(img_path, use_container_width=True)

    # 2. 基本信息卡片
    st.markdown(f"""
    <div class="info-box">
        <div class="info-title">基本信息</div>
        <div class="info-row"><span>👥 <b>類別</b></span><span>{category}</span></div>
        <div class="info-row"><span>💲 <b>價格</b></span><span>¥{price:.2f}</span></div>
        <div class="info-row"><span>🕒 <b>上次穿著</b></span><span>{last_worn}</span></div>
        <div class="info-row"><span>🏷️ <b>單次成本</b></span><span>¥{avg_cost:.2f} / 次</span></div>
        <div class="info-row"><span>🛒 <b>購買年份</b></span><span>{purchase_year}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # 3. 穿著次數快捷加減按鈕
    st.write("🔄 **穿著次數調整**")
    w_col1, w_col2, w_col3 = st.columns([1, 2, 1])
    with w_col1:
        if st.button("➖ 減 1 次", use_container_width=True, disabled=(wear_count <= 0)):
            update_wear_count(cid, -1)
            st.rerun()
    with w_col2:
        st.metric(label="累計穿著", value=f"{wear_count} 次", delta=None)
    with w_col3:
        if st.button("➕ 今天穿 (+1)", type="primary", use_container_width=True):
            update_wear_count(cid, 1)
            st.toast("已為您記錄今天穿著！")
            st.rerun()

    # 4. 季節信息卡片
    st.markdown(f"""
    <div class="info-box">
        <div class="info-title">季節信息</div>
        <div><span class="season-chip">✓ {seasons}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # 5. 編輯詳情 / 刪除
    with st.expander("⚙️ 編輯資訊或刪除衣物"):
        edit_name = st.text_input("衣服名稱", value=name)
        edit_price = st.number_input("價格 (¥)", value=float(price), step=10.0)
        
        all_cats = get_categories()
        edit_cat = st.selectbox("修改分類", all_cats, index=all_cats.index(category) if category in all_cats else 0)
        edit_year = st.text_input("購買年份", value=purchase_year)
        edit_seasons = st.selectbox("適用季節", ["全季節", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"], index=0)
        
        btn_e1, btn_e2 = st.columns(2)
        with btn_e1:
            if st.button("💾 儲存修改", use_container_width=True):
                update_clothing_info(cid, edit_name, edit_price, edit_cat, edit_year, edit_seasons)
                st.success("資訊已更新！")
                st.rerun()
        with btn_e2:
            if st.button("🗑️ 刪除此衣物", type="secondary", use_container_width=True):
                delete_clothing(cid, img_path)
                st.session_state.selected_id = None
                st.rerun()

# ==========================================
# 主分頁視圖
# ==========================================
else:
    st.title("👗 智慧衣櫃")
    tab_wardrobe, tab_add, tab_category = st.tabs(["🧥 我的衣櫃", "➕ 新增衣服", "🏷️ 分類管理"])

    # ===== 分頁 1: 我的衣櫃 =====
    with tab_wardrobe:
        categories = ["全部"] + get_categories()
        selected_cat = st.segmented_control("分類篩選", categories, default="全部")
        
        items = get_clothes(category_filter=selected_cat)
        
        if not items:
            st.info("尚無衣物，請點選「新增衣服」分頁建立！")
        else:
            cols = st.columns(2)
            for idx, item in enumerate(items):
                cid, name, price, wear_count, img_path, cat, p_year, _, _ = item
                avg_cost = price / wear_count if wear_count > 0 else price
                
                with cols[idx % 2]:
                    if os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    st.markdown(f"**{name}** · `{cat}`")
                    st.caption(f"原價 ¥{price:.1f} | 穿著 {wear_count} 次 | **¥{avg_cost:.1f}/次**")
                    if st.button("🔍 查看詳情", key=f"view_{cid}", use_container_width=True):
                        st.session_state.selected_id = cid
                        st.rerun()
                    st.markdown("---")

    # ===== 分頁 2: 新增衣服 (含圖片裁切) =====
    with tab_add:
        st.subheader("新增衣物")
        
        item_name = st.text_input("衣物名稱", placeholder="例如：純棉淺色條紋襯衫")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            item_price = st.number_input("購買價格 (¥)", min_value=0.1, step=10.0, value=149.0)
            avail_cats = get_categories()
            item_cat = st.selectbox("選擇分類", avail_cats)
        with col_c2:
            current_year = str(datetime.now().year)
            item_year = st.text_input("購買年份", value=current_year)
            item_seasons = st.selectbox("適用季節", ["全季節", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"])

        upload_method = st.radio("圖片來源", ["📸 相機拍照", "📁 相簿上傳"], horizontal=True)
        raw_image_data = None
        if "拍照" in upload_method:
            camera_file = st.camera_input("拍照")
            if camera_file:
                raw_image_data = camera_file.getvalue()
        else:
            uploaded_file = st.file_uploader("選擇圖片", type=["jpg", "jpeg", "png"])
            if uploaded_file:
                raw_image_data = uploaded_file.getvalue()

        cropped_img = None
        if raw_image_data:
            st.write("✂️ **拖曳選框進行圖片裁切：**")
            image_obj = Image.open(io.BytesIO(raw_image_data))
            cropped_img = st_cropper(
                image_obj,
                realtime_update=True,
                box_color="#4CAF50",
                aspect_ratio=None
            )
            
        if st.button("💾 儲存並加入衣櫃", type="primary", use_container_width=True):
            if not item_name.strip():
                st.error("請填寫衣物名稱")
            elif cropped_img is None:
                st.error("請提供並確認衣物圖片")
            else:
                add_clothing(item_name.strip(), item_price, item_cat, item_year, item_seasons, cropped_img)
                st.success("✅ 已成功加入衣櫃！")
                st.rerun()

    # ===== 分頁 3: 分類管理 =====
    with tab_category:
        st.subheader("🏷️ 自定義衣物分類")
        
        new_cat = st.text_input("新增自定義分類名稱", placeholder="例如：運動服、居家服、復古款")
        if st.button("➕ 新增分類"):
            if new_cat.strip():
                add_category(new_cat)
                st.toast(f"已新增分類：{new_cat}")
                st.rerun()
                
        st.markdown("---")
        st.write("**目前現有分類列表：**")
        all_c = get_categories()
        st.write("、".join([f"`{c}`" for c in all_c]))

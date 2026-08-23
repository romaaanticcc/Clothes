import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image, ImageOps
import io
from streamlit_cropper import st_cropper

# 支持 iPhone HEIC 格式
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

st.set_page_config(page_title="我的衣橱", page_icon="👗", layout="centered")

DB_FILE = "wardrobe.db"
UPLOAD_DIR = "uploaded_clothes"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ----------------- 自定义 CSS（还原 App 风格） -----------------
st.markdown("""
<style>
    /* 全局字体与背景微调 */
    .stApp {
        background-color: #f7f9f7;
    }
    
    /* 顶部数据看板 */
    .top-stats {
        display: flex;
        align-items: center;
        gap: 16px;
        font-size: 18px;
        font-weight: 700;
        color: #2b512a;
        margin-bottom: 8px;
    }
    
    /* 横向衣服卡片容器 */
    .clothing-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 12px 14px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        border: 1px solid #edf2ed;
    }
    
    /* 卡片内文字样式 */
    .cpw-price {
        font-size: 19px;
        font-weight: 800;
        color: #1b381b;
        margin-bottom: 3px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .sub-info {
        font-size: 14px;
        color: #7a8b7a;
    }
    
    /* 圆形加号按钮样式 */
    div[data-testid="stButton"] > button[kind="primary"] {
        border-radius: 50%;
        background-color: #34c759;
        border: none;
        color: white;
        font-size: 20px;
        font-weight: bold;
        padding: 0;
        height: 42px;
        width: 42px;
        box-shadow: 0 3px 6px rgba(52, 199, 89, 0.3);
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #2eb350;
        color: white;
    }

    /* 详情卡片与标签样式 */
    .detail-box {
        background-color: #ecf6ed;
        border-radius: 18px;
        padding: 18px 20px;
        margin: 12px 0;
        color: #1e3a1e;
    }
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        font-size: 15px;
    }
    .season-pill {
        display: inline-block;
        background: #ffffff;
        padding: 5px 12px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        color: #2b512a;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 数据库操作 -----------------
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
            last_worn TEXT DEFAULT '暂无',
            seasons TEXT DEFAULT '全季节'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    defaults = ['上衣', '裤子', '裙子', '外套', '鞋靴', '配件']
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
           VALUES (?, ?, 0, ?, ?, ?, ?, '暂无', ?)''',
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

# 页面状态
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "衣橱"

# ==========================================
# 1. 详情视图 (点击衣服进入)
# ==========================================
if st.session_state.selected_id is not None:
    item = get_clothing_by_id(st.session_state.selected_id)
    if not item:
        st.session_state.selected_id = None
        st.rerun()

    cid, name, price, wear_count, img_path, category, purchase_year, last_worn, seasons = item
    avg_cost = price / wear_count if wear_count > 0 else price

    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("⬅ 返回"):
            st.session_state.selected_id = None
            st.rerun()

    st.subheader(f"衣物详情 · {name}")

    if os.path.exists(img_path):
        st.image(img_path, use_container_width=True)

    st.markdown(f"""
    <div class="detail-box">
        <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">基本信息</div>
        <div class="detail-row"><span>👥 类别</span><span><b>{category}</b></span></div>
        <div class="detail-row"><span>💰 价格</span><span>¥{price:.2f}</span></div>
        <div class="detail-row"><span>🔄 穿着次数</span><span>{wear_count} 次</span></div>
        <div class="detail-row"><span>🕒 上次穿着</span><span>{last_worn}</span></div>
        <div class="detail-row"><span>🏷️ 单次成本</span><span><b>¥{avg_cost:.2f} / 次</b></span></div>
        <div class="detail-row"><span>🛒 购买年份</span><span>{purchase_year}</span></div>
    </div>
    <div class="detail-box">
        <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">季节信息</div>
        <div><span class="season-pill">✓ {seasons}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # 快捷次数操作
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ 今天穿 (+1)", key="dt_add", type="primary", use_container_width=True):
            update_wear_count(cid, 1)
            st.toast("已更新穿着记录！")
            st.rerun()
    with c_btn2:
        if st.button("➖ 撤回 (-1)", key="dt_sub", use_container_width=True, disabled=(wear_count <= 0)):
            update_wear_count(cid, -1)
            st.rerun()

    with st.expander("⚙️ 编辑衣物资料 / 删除"):
        edit_name = st.text_input("名称", value=name)
        edit_price = st.number_input("价格 (¥)", value=float(price), step=10.0)
        cats = get_categories()
        edit_cat = st.selectbox("分类", cats, index=cats.index(category) if category in cats else 0)
        edit_year = st.text_input("年份", value=purchase_year)
        edit_season = st.selectbox("季节", ["全季节", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"], index=0)

        e1, e2 = st.columns(2)
        with e1:
            if st.button("💾 保存修改", use_container_width=True):
                update_clothing_info(cid, edit_name, edit_price, edit_cat, edit_year, edit_season)
                st.success("已更新！")
                st.rerun()
        with e2:
            if st.button("🗑️ 删除衣服", type="secondary", use_container_width=True):
                delete_clothing(cid, img_path)
                st.session_state.selected_id = None
                st.rerun()

# ==========================================
# 2. 主清单界面 (对标截图风格)
# ==========================================
else:
    # 顶部导航切换
    nav_selected = st.segmented_control(
        "导航",
        ["🧥 我的衣橱", "➕ 新增衣服", "🏷️ 分类管理"],
        default="🧥 我的衣橱",
        label_visibility="collapsed"
    )

    # ===== 分页：衣橱清单 =====
    if nav_selected == "🧥 我的衣橱":
        all_items = get_clothes("全部")
        total_items = len(all_items)
        total_spent = sum(x[2] for x in all_items)

        # 顶部统计指标
        st.markdown(f"""
        <div class="top-stats">
            <span>👕 {total_items}</span>
            <span>💰 ¥{total_spent:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)

        # 顶部胶囊列 (Pills)
        categories = ["全部"] + get_categories()
        selected_cat = st.pills("分类筛选", categories, default="全部", label_visibility="collapsed")
        
        target_cat = selected_cat if selected_cat else "全部"
        displayed_items = get_clothes(target_cat)

        # 类别与数量标题
        st.markdown(f"#### {target_cat} ({len(displayed_items)})")

        if not displayed_items:
            st.info("该分类下暂无衣物，请点击「➕ 新增衣服」上传！")
        else:
            # 横向卡片列表展示
            for item in displayed_items:
                cid, name, price, wear_count, img_path, cat, p_year, _, _ = item
                avg_cost = price / wear_count if wear_count > 0 else price

                with st.container():
                    col_img, col_info, col_action = st.columns([1.1, 2.5, 0.8], vertical_alignment="center")
                    
                    with col_img:
                        if os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                    
                    with col_info:
                        st.markdown(f"<div class='cpw-price'>¥{avg_cost:.2f}/次</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='sub-info'>¥{price:.0f} &nbsp;&nbsp; 已穿 {wear_count} 次</div>", unsafe_allow_html=True)
                        if st.button("详情 ❯", key=f"det_{cid}", type="tertiary"):
                            st.session_state.selected_id = cid
                            st.rerun()

                    with col_action:
                        if st.button("＋", key=f"btn_add_{cid}", type="primary", help="打卡穿着 +1"):
                            update_wear_count(cid, 1)
                            st.toast(f"已记录！{name} 穿着 +1", icon="👕")
                            st.rerun()
                    
                    st.divider()

    # ===== 分页：新增衣服 (含相机/上传与裁切) =====
    elif nav_selected == "➕ 新增衣服":
        st.subheader("新增衣物")
        
        item_name = st.text_input("衣物名称", placeholder="例如：绿色无袖上衣")
        
        col1, col2 = st.columns(2)
        with col1:
            item_price = st.number_input("购买价格 (¥)", min_value=0.1, step=10.0, value=55.0)
            avail_cats = get_categories()
            item_cat = st.selectbox("选择分类", avail_cats)
        with col2:
            item_year = st.text_input("购买年份", value=str(datetime.now().year))
            item_seasons = st.selectbox("适用季节", ["全季节", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"])

        upload_type = st.radio("照片来源", ["📸 相机拍照", "📁 相册上传"], horizontal=True)
        raw_img_bytes = None
        
        if "拍照" in upload_type:
            cam = st.camera_input("拍照")
            if cam:
                raw_img_bytes = cam.getvalue()
        else:
            up = st.file_uploader("选择照片", type=["jpg", "jpeg", "png", "heic", "heif"])
            if up:
                raw_img_bytes = up.getvalue()

        cropped_img = None
        if raw_img_bytes:
            try:
                st.write("✂️ **拖拽选框进行图片裁切：**")
                img_obj = Image.open(io.BytesIO(raw_img_bytes))
                img_obj = ImageOps.exif_transpose(img_obj)
                
                cropped_img = st_cropper(
                    img_obj,
                    realtime_update=True,
                    box_color="#34c759",
                    aspect_ratio=(3, 4)
                )
            except Exception:
                st.error("图片读取失败，请确认文件格式是否正确。")

        if st.button("💾 保存并加入衣橱", type="primary", use_container_width=True):
            if not item_name.strip():
                st.error("请输入衣服名称")
            elif cropped_img is None:
                st.error("请提供衣物照片")
            else:
                add_clothing(item_name.strip(), item_price, item_cat, item_year, item_seasons, cropped_img)
                st.success("✅ 成功加入衣橱！")
                st.rerun()

    # ===== 分页：分类管理 =====
    elif nav_selected == "🏷️ 分类管理":
        st.subheader("分类设置")
        new_c = st.text_input("自定义新分类名称", placeholder="例如：洋装、运动服")
        if st.button("➕ 新增分类"):
            if new_c.strip():
                add_category(new_c)
                st.toast(f"已新增分类：{new_c}")
                st.rerun()
        
        st.divider()
        st.write("**当前分类标签：**")
        st.write("、".join([f"`{c}`" for c in get_categories()]))

import streamlit as st
import sqlite3
import os
import uuid
import base64
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

def get_image_base64(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

# ----------------- 终极移动端布局：防溢出 + 纯色圆形按钮 -----------------
st.markdown("""
<style>
    /* 1. 彻底禁用全局横向滚动 */
    .stApp, .main {
        overflow-x: hidden !important;
        background-color: #f7f9f7;
    }

    /* 2. 锁定手机屏幕宽度 */
    .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 0.5rem !important;
        max-width: 420px !important;
        margin: 0 auto !important;
        overflow-x: hidden !important;
    }

    .top-stats {
        display: flex;
        align-items: center;
        gap: 16px;
        font-size: 20px;
        font-weight: 700;
        color: #1b381b;
        margin-bottom: 12px;
        margin-top: 4px;
    }

    div[data-testid="stPills"] button {
        border-radius: 20px !important;
        border: none !important;
        background-color: #e8eae8 !important;
        color: #333333 !important;
        font-size: 13px !important;
        padding: 4px 12px !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"] {
        background-color: #34c759 !important;
        color: white !important;
    }

    /* ========================================================= */
    /* 核心卡片布局：强制单行，最右侧留给按钮 */
    /* ========================================================= */
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important; /* 绝对禁止换行 */
        align-items: center !important;
        justify-content: space-between !important;
        background-color: #ffffff;
        border-radius: 18px;
        padding: 10px 8px 10px 10px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        border: 1px solid #f2f4f2;
        margin-bottom: 12px;
        gap: 6px !important; /* 按钮之间的微小间距 */
        width: 100% !important;
        box-sizing: border-box !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"] {
        width: auto !important;
        min-width: 0 !important;
        flex: none !important;
        padding: 0 !important;
    }

    /* 第 1 列：左侧图片与文本区（自适应拉伸并截断超长文字） */
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(1) {
        flex: 1 1 auto !important;
        width: 100% !important;
        overflow: hidden !important;
    }
    
    /* 第 2, 3, 4 列：右侧三个按钮的严格定宽 */
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(2),
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(3),
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(4) {
        flex: 0 0 32px !important;
        width: 32px !important;
        display: flex !important;
        justify-content: center !important;
    }

    /* ========================================================= */
    /* 按钮外观重置：纯圆、无边框、强制文字/图标变白 */
    /* ========================================================= */
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) button {
        border-radius: 50% !important;
        width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
    }

    /* 暴力覆盖 Streamlit 原生字体颜色 */
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) button * {
        color: #ffffff !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.card-left-box) button:active {
        opacity: 0.7 !important;
        transform: scale(0.92) !important;
    }

    /* 🔴【黑色】详情按钮 */
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(2) button {
        background-color: #2c2c2e !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(2) button * {
        font-size: 16px !important;
        font-family: serif !important;
        font-style: italic !important;
    }

    /* 🟢【绿色】＋号按钮 */
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(3) button {
        background-color: #34c759 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(3) button * {
        font-size: 20px !important;
    }

    /* 🔴【红色】－号按钮 */
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(4) button {
        background-color: #ff3b30 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.card-left-box) > div[data-testid="column"]:nth-child(4) button * {
        font-size: 20px !important;
    }

    /* ========================================================= */
    /* 卡片内部图文排版 */
    /* ========================================================= */
    .card-left-box {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
    }
    .card-img {
        width: 52px;
        height: 52px;
        border-radius: 12px;
        object-fit: cover;
        flex-shrink: 0;
        background-color: #f0f0f0;
    }
    .card-text-col {
        display: flex;
        flex-direction: column;
        min-width: 0; /* 防止子元素撑破父级 */
    }
    .cpw-price {
        font-size: 16px;
        font-weight: 800;
        color: #1c1c1e;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .sub-info {
        font-size: 12px;
        color: #8e8e93;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .detail-box {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 16px 18px;
        margin: 12px 0;
        color: #1e3a1e;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        font-size: 15px;
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
    defaults = ['上衣', '裤子', '外套', '洋装', '鞋靴', '包包配件', '裙子', '配件']
    for cat in defaults:
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))
    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM categories ORDER BY id ASC")
    return [r[0] for r in c.fetchall()]

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
        try: os.remove(image_path)
        except Exception: pass
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM clothes WHERE id = ?", (clothing_id,))
    conn.commit()
    conn.close()

init_db()

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

# ==========================================
# 1. 详情视图
# ==========================================
if st.session_state.selected_id is not None:
    item = get_clothing_by_id(st.session_state.selected_id)
    if not item:
        st.session_state.selected_id = None
        st.rerun()

    cid, name, price, wear_count, img_path, category, purchase_year, last_worn, seasons = item
    avg_cost = price / wear_count if wear_count > 0 else price

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
    """, unsafe_allow_html=True)

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
# 2. 主界面
# ==========================================
else:
    nav_selected = st.segmented_control(
        "导航",
        ["👚 我的衣橱", "➕ 新增衣服", "🏷️ 分类管理"],
        default="👚 我的衣橱",
        label_visibility="collapsed"
    )

    if nav_selected == "👚 我的衣橱":
        all_items = get_clothes("全部")
        total_items = len(all_items)
        total_spent = sum(x[2] for x in all_items)

        st.markdown(f"""
        <div class="top-stats">
            <span>👕 {total_items}</span>
            <span>💰 {total_spent:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)

        categories = ["全部"] + get_categories()
        selected_cat = st.pills("分类筛选", categories, default="全部", label_visibility="collapsed")

        target_cat = selected_cat if selected_cat else "全部"
        displayed_items = get_clothes(target_cat)

        st.markdown(f"### {target_cat} ({len(displayed_items)})")

        if not displayed_items:
            st.info("该分类下暂无衣物，请选择「➕ 新增衣服」上传！")
        else:
            for item in displayed_items:
                cid, name, price, wear_count, img_path, cat, p_year, _, _ = item
                avg_cost = price / wear_count if wear_count > 0 else price
                img_b64 = get_image_base64(img_path)

                # 使用比例划分：左侧信息区占满，右侧预留出足够的按钮空间
                c1, c2, c3, c4 = st.columns([0.65, 0.11, 0.12, 0.12], vertical_alignment="center")

                with c1:
                    # 使用 card-text-col 限制文本宽度自动截断，保护右侧按钮不被挤压
                    st.markdown(f"""
                    <div class="card-left-box">
                        <img src="data:image/jpeg;base64,{img_b64}" class="card-img">
                        <div class="card-text-col">
                            <div class="cpw-price">¥{avg_cost:.2f}/次</div>
                            <div class="sub-info">¥{price:.0f} 已穿 {wear_count} 次</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with c2:
                    # 黑色的详情按钮 (CSS控制变为圆形)
                    if st.button("i", key=f"det_{cid}"):
                        st.session_state.selected_id = cid
                        st.rerun()

                with c3:
                    # 绿色的 + 号按钮
                    if st.button("＋", key=f"add_{cid}"):
                        update_wear_count(cid, 1)
                        st.toast("已记录穿着！", icon="👕")
                        st.rerun()

                with c4:
                    # 红色的 - 号按钮
                    if st.button("－", key=f"sub_{cid}", disabled=(wear_count <= 0)):
                        update_wear_count(cid, -1)
                        st.toast("已撤回穿着！")
                        st.rerun()

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
            item_seasons = st.selectbox("使用季节", ["全季节", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"])

        st.write("📁 **相册上传**")
        up = st.file_uploader("选择照片", type=["jpg", "jpeg", "png", "heic", "heif"], label_visibility="collapsed")
        raw_img_bytes = up.getvalue() if up else None

        if up:
            st.success("✅ 图片上传成功！")

        cropped_img = None
        if raw_img_bytes:
            try:
                st.write("✂️ **拖拽选框进行自由裁切：**")
                img_obj = Image.open(io.BytesIO(raw_img_bytes))
                img_obj = ImageOps.exif_transpose(img_obj)

                cropped_img = st_cropper(
                    img_obj,
                    realtime_update=True,
                    box_color="#34c759",
                    aspect_ratio=None
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

    elif nav_selected == "🏷️ 分类管理":
        st.subheader("分类设置")
        new_c = st.text_input("自定义新分类名称", placeholder="例如：连衣裙、运动服")
        if st.button("➕ 新增分类"):
            if new_c.strip():
                add_category(new_c)
                st.toast(f"已新增分类：{new_c}")
                st.rerun()

        st.divider()
        st.write("**当前分类标签：**")
        st.write("、".join([f"`{c}`" for c in get_categories()]))

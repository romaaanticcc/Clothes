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

# ----------------- 自定义 CSS（完全仿图2样式） -----------------
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {
        background-color: #f7f9f7;
    }
    
    .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 0.3rem !important;
        max-width: 100% !important;
    }
    
    /* 顶部统计 - 仿图2 */
    .top-stats {
        display: flex;
        align-items: center;
        gap: 14px;
        font-size: 20px;
        font-weight: 700;
        color: #1b381b;
        margin-bottom: 10px;
        margin-top: 2px;
    }
    .top-stats span {
        background: white;
        padding: 3px 16px;
        border-radius: 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    
    /* 分类筛选 - 仿图2胶囊 */
    div[data-testid="stPills"] {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-bottom: 10px;
    }
    div[data-testid="stPills"] button {
        border-radius: 20px !important;
        border: none !important;
        background-color: #eef1ee !important;
        color: #555555 !important;
        font-size: 13px !important;
        padding: 4px 16px !important;
        margin: 0 !important;
        font-weight: 500 !important;
        min-height: 32px !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"] {
        background-color: #2c6b2c !important;
        color: white !important;
    }
    
    /* 分类标题 - 仿图2 */
    .category-title {
        font-size: 18px;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 12px;
        margin-top: 4px;
    }
    
    /* ============================================================
       卡片样式 - 完全仿图2
       ============================================================ */
    .clothing-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #ffffff;
        border-radius: 14px;
        padding: 10px 14px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
        border: 1px solid #eef1ee;
        min-height: 66px;
    }
    
    .card-left {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        min-width: 0;
    }
    
    .card-img {
        width: 50px;
        height: 50px;
        border-radius: 10px;
        object-fit: cover;
        flex-shrink: 0;
        background-color: #f0f0f0;
        border: 1px solid #e8ece8;
    }
    
    .card-info {
        display: flex;
        flex-direction: column;
        min-width: 0;
    }
    
    .card-price {
        font-size: 16px;
        font-weight: 800;
        color: #1a1a1a;
        line-height: 1.3;
    }
    
    .card-sub {
        font-size: 12px;
        color: #8e8e93;
        line-height: 1.4;
    }
    
    .card-right {
        flex-shrink: 0;
        margin-left: 8px;
    }
    
    /* 绿色加号按钮 - 仿图2 */
    .card-right button {
        border-radius: 50% !important;
        width: 36px !important;
        height: 36px !important;
        min-height: 36px !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        background-color: #34c759 !important;
        color: white !important;
        font-size: 20px !important;
        font-weight: 300 !important;
        box-shadow: 0 2px 8px rgba(52, 199, 89, 0.3) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        line-height: 1 !important;
    }
    .card-right button:active {
        transform: scale(0.85) !important;
    }
    
    /* 详情按钮 - 文字链接样式 */
    .detail-link {
        background: none !important;
        border: none !important;
        color: #34c759 !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 2px 0 !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        width: auto !important;
        min-height: auto !important;
        cursor: pointer !important;
    }
    .detail-link:hover {
        text-decoration: underline !important;
        color: #28a745 !important;
    }
    
    /* 详情页样式 */
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
        padding: 8px 0;
        font-size: 15px;
        border-bottom: 1px solid #dce8dc;
    }
    .detail-row:last-child {
        border-bottom: none;
    }
    .season-pill {
        display: inline-block;
        background: #ffffff;
        padding: 4px 14px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        color: #2b512a;
    }
    
    /* 隐藏默认按钮样式 */
    .stButton > button {
        border-radius: 50% !important;
    }
    .row-widget.stColumns {
        gap: 0 !important;
    }
    .row-widget.stColumns > div {
        padding: 0 !important;
    }
    
    /* 手机适配 */
    @media (max-width: 640px) {
        .clothing-card {
            padding: 8px 10px;
            min-height: 58px;
        }
        .card-img {
            width: 42px;
            height: 42px;
        }
        .card-price {
            font-size: 14px;
        }
        .card-sub {
            font-size: 11px;
        }
        .card-right button {
            width: 32px !important;
            height: 32px !important;
            min-height: 32px !important;
            font-size: 18px !important;
        }
        .top-stats {
            font-size: 17px;
            gap: 10px;
        }
        .top-stats span {
            padding: 2px 12px;
        }
        div[data-testid="stPills"] button {
            font-size: 12px !important;
            padding: 3px 12px !important;
            min-height: 28px !important;
        }
        .category-title {
            font-size: 16px;
        }
    }
    
    @media (max-width: 400px) {
        .card-img {
            width: 36px;
            height: 36px;
        }
        .card-price {
            font-size: 12px;
        }
        .card-sub {
            font-size: 10px;
        }
        .card-right button {
            width: 28px !important;
            height: 28px !important;
            min-height: 28px !important;
            font-size: 15px !important;
        }
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

def delete_category(cat_name):
    if cat_name.strip() and cat_name not in ['上衣', '裤子', '裙子', '外套', '鞋靴', '配件']:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        # 先将该分类下的衣服移到"上衣"
        c.execute("UPDATE clothes SET category = '上衣' WHERE category = ?", (cat_name,))
        c.execute("DELETE FROM categories WHERE name = ?", (cat_name,))
        conn.commit()
        conn.close()
        return True
    return False

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
if "show_success" not in st.session_state:
    st.session_state.show_success = False
if "success_message" not in st.session_state:
    st.session_state.success_message = ""

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
        <div class="detail-row"><span>类别</span><span><b>{category}</b></span></div>
        <div class="detail-row"><span>价格</span><span>¥{price:.2f}</span></div>
        <div class="detail-row"><span>穿着次数</span><span>{wear_count} 次</span></div>
        <div class="detail-row"><span>上次穿着</span><span>{last_worn}</span></div>
        <div class="detail-row"><span>单次成本</span><span><b>¥{avg_cost:.2f} / 次</b></span></div>
        <div class="detail-row"><span>购买年份</span><span>{purchase_year}</span></div>
    </div>
    <div class="detail-box">
        <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">季节信息</div>
        <div><span class="season-pill">✓ {seasons}</span></div>
    </div>
    """, unsafe_allow_html=True)

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("➕ 今天穿 (+1)", key="dt_add", type="primary", use_container_width=True):
            update_wear_count(cid, 1)
            st.toast("已更新穿着记录！", icon="👕")
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
        edit_season = st.selectbox("季节", ["全季节", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"], 
                                   index=["全季节", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"].index(seasons) if seasons in ["全季节", "春季", "夏季", "秋季", "冬季", "春夏", "秋冬"] else 0)

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
# 2. 主界面 - 完全仿图2
# ==========================================
else:
    nav_selected = st.segmented_control(
        "导航",
        ["🧥 我的衣橱", "➕ 新增衣服", "🏷️ 分类管理"],
        default="🧥 我的衣橱",
        label_visibility="collapsed"
    )

    # ===== 衣橱列表 =====
    if nav_selected == "🧥 我的衣橱":
        all_items = get_clothes("全部")
        total_items = len(all_items)
        total_spent = sum(x[2] for x in all_items)

        # 顶部统计 - 仿图2
        st.markdown(f"""
        <div class="top-stats">
            <span>👕 {total_items}</span>
            <span>💰 ¥{total_spent:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)

        # 分类筛选 - 仿图2
        categories = ["全部"] + get_categories()
        selected_cat = st.pills("分类筛选", categories, default="全部", label_visibility="collapsed")
        
        target_cat = selected_cat if selected_cat else "全部"
        displayed_items = get_clothes(target_cat)

        # 分类标题 - 仿图2
        st.markdown(f'<div class="category-title">{target_cat} ({len(displayed_items)})</div>', unsafe_allow_html=True)

        if not displayed_items:
            st.info("该分类下暂无衣物，请点击「➕ 新增衣服」上传！")
        else:
            for item in displayed_items:
                cid, name, price, wear_count, img_path, cat, p_year, _, _ = item
                avg_cost = price / wear_count if wear_count > 0 else price
                
                # 获取图片base64
                img_b64 = ""
                if os.path.exists(img_path):
                    import base64
                    with open(img_path, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode()

                # 卡片HTML - 仿图2
                st.markdown(f'''
                <div class="clothing-card">
                    <div class="card-left">
                        <img src="data:image/jpeg;base64,{img_b64}" class="card-img">
                        <div class="card-info">
                            <div class="card-price">¥{avg_cost:.2f}/次</div>
                            <div class="card-sub">¥{price:.0f} · 已穿 {wear_count} 次</div>
                        </div>
                    </div>
                    <div class="card-right" id="btn-{cid}"></div>
                </div>
                ''', unsafe_allow_html=True)

                # 使用两列：详情按钮（左）+ 加号按钮（右）
                col_detail, col_plus = st.columns([0.7, 0.3])

                with col_detail:
                    # 详情 - 文字链接样式
                    if st.button("详情 ❯", key=f"det_{cid}", use_container_width=False):
                        st.session_state.selected_id = cid
                        st.rerun()
                    # 覆盖样式为文字链接
                    st.markdown('''
                    <style>
                        div[data-testid="column"]:first-child button {
                            background: none !important;
                            border: none !important;
                            color: #34c759 !important;
                            font-weight: 600 !important;
                            font-size: 13px !important;
                            padding: 2px 0 !important;
                            box-shadow: none !important;
                            border-radius: 0 !important;
                            width: auto !important;
                            min-height: auto !important;
                        }
                        div[data-testid="column"]:first-child button:hover {
                            text-decoration: underline !important;
                            color: #28a745 !important;
                        }
                        div[data-testid="column"]:first-child button:active {
                            transform: none !important;
                            opacity: 0.7 !important;
                        }
                    </style>
                    ''', unsafe_allow_html=True)

                with col_plus:
                    # 绿色加号按钮 - 仿图2
                    if st.button("＋", key=f"add_{cid}", use_container_width=True):
                        update_wear_count(cid, 1)
                        st.toast(f"已记录！{name} +1次", icon="👕")
                        st.rerun()
                    # 覆盖样式为绿色圆形
                    st.markdown('''
                    <style>
                        div[data-testid="column"]:last-child button {
                            border-radius: 50% !important;
                            background-color: #34c759 !important;
                            color: white !important;
                            font-size: 20px !important;
                            font-weight: 300 !important;
                            border: none !important;
                            box-shadow: 0 2px 8px rgba(52, 199, 89, 0.3) !important;
                            width: 36px !important;
                            height: 36px !important;
                            min-height: 36px !important;
                            padding: 0 !important;
                            display: flex !important;
                            align-items: center !important;
                            justify-content: center !important;
                            margin: 0 auto !important;
                        }
                        div[data-testid="column"]:last-child button:active {
                            transform: scale(0.85) !important;
                        }
                        @media (max-width: 640px) {
                            div[data-testid="column"]:last-child button {
                                width: 32px !important;
                                height: 32px !important;
                                min-height: 32px !important;
                                font-size: 18px !important;
                            }
                        }
                    </style>
                    ''', unsafe_allow_html=True)

    # ===== 新增衣服 - 仅相册上传 =====
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

        st.write("📁 **从相册上传照片**")
        up = st.file_uploader("选择照片", type=["jpg", "jpeg", "png", "heic", "heif"], label_visibility="collapsed")
        
        if up:
            st.success("✅ 图片上传成功！请裁剪")
            raw_img_bytes = up.getvalue()
        else:
            raw_img_bytes = None

        cropped_img = None
        if raw_img_bytes:
            try:
                st.write("✂️ **拖拽选框进行裁剪：**")
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
                st.error("请上传并裁剪衣物照片")
            else:
                add_clothing(item_name.strip(), item_price, item_cat, item_year, item_seasons, cropped_img)
                st.success("✅ 成功加入衣橱！")
                st.balloons()
                st.rerun()

    # ===== 分类管理（含删除功能） =====
    elif nav_selected == "🏷️ 分类管理":
        st.subheader("分类管理")
        
        # 新增分类
        new_c = st.text_input("自定义新分类名称", placeholder="例如：连衣裙、运动服")
        if st.button("➕ 新增分类"):
            if new_c.strip():
                add_category(new_c)
                st.toast(f"已新增分类：{new_c}", icon="✅")
                st.rerun()
        
        st.divider()
        
        # 显示所有分类并提供删除
        st.write("**当前分类标签：**")
        cats = get_categories()
        
        # 默认分类不可删除
        default_cats = ['上衣', '裤子', '裙子', '外套', '鞋靴', '配件']
        
        for cat in cats:
            col_cat, col_del = st.columns([3, 1])
            with col_cat:
                st.write(f"• {cat}")
            with col_del:
                if cat not in default_cats:
                    if st.button("🗑️", key=f"del_cat_{cat}"):
                        if delete_category(cat):
                            st.toast(f"已删除分类：{cat}", icon="🗑️")
                            st.rerun()
                        else:
                            st.error("删除失败，请重试")
                else:
                    st.write("(默认)")
        
        st.info("💡 默认分类不可删除，删除自定义分类后，该分类下的衣物将移至「上衣」")

import streamlit as st
import sqlite3
import os
import uuid
from datetime import datetime
from PIL import Image
import io

# 设定页面配置
st.set_page_config(page_title="Smart Wardrobe - Cost Per Wear", page_icon="👗", layout="wide")

DB_FILE = "wardrobe.db"
UPLOAD_DIR = "uploaded_clothes"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ----------------- 资料库操作 -----------------
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
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_clothing(name, price, image_bytes):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    filename = f"{uuid.uuid4().hex}.jpg"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    img = Image.open(io.BytesIO(image_bytes))
    img.convert('RGB').save(file_path, "JPEG", quality=85)
    
    c.execute(
        "INSERT INTO clothes (name, price, wear_count, image_path, created_at) VALUES (?, ?, 0, ?, ?)",
        (name, price, file_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def get_clothes():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, price, wear_count, image_path FROM clothes ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def increment_wear_count(clothing_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE clothes SET wear_count = wear_count + 1 WHERE id = ?", (clothing_id,))
    conn.commit()
    conn.close()

def decrement_wear_count(clothing_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 确保次数不会小于 0
    c.execute("UPDATE clothes SET wear_count = MAX(0, wear_count - 1) WHERE id = ?", (clothing_id,))
    conn.commit()
    conn.close()

def update_clothing(clothing_id, name, price, wear_count):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE clothes SET name = ?, price = ?, wear_count = ? WHERE id = ?",
        (name, price, wear_count, clothing_id)
    )
    conn.commit()
    conn.close()

def delete_clothing(clothing_id, image_path):
    # 刪除实物图片
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
        except Exception:
            pass
    # 刪除资料库记录
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM clothes WHERE id = ?", (clothing_id,))
    conn.commit()
    conn.close()

# ----------------- 主畫面 -----------------
init_db()

st.title("👗 智慧衣柜")

tab_wardrobe, tab_add, tab_stats = st.tabs(["🧥 我的衣柜", "➕ 新增衣服", "📊 数据分析"])

# ===== 分页 1: 我的衣柜 =====
with tab_wardrobe:
    items = get_clothes()
    
    if not items:
        st.info("衣柜目前是空的，快去「新增衣服」分页拍照上传吧！")
    else:
        cols = st.columns(3)
        for idx, item in enumerate(items):
            cid, name, price, wear_count, img_path = item
            avg_cost = price / wear_count if wear_count > 0 else price
            
            with cols[idx % 3]:
                st.markdown(f"### {name}")
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                
                st.write(f"💰 **购买原价**：¥{price:.1f}")
                st.write(f"🔢 **穿着次数**：{wear_count} 次")
                
                if wear_count == 0:
                    st.warning(f"🏷️ **当前均价**：¥{avg_cost:.1f}（尚未穿過）")
                else:
                    st.success(f"🏷️ **当前均价**：¥{avg_cost:.2f} / 次")
                
                # 打卡與撤回按鈕
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button("✨ 今天穿 (+1)", key=f"add_{cid}", use_container_width=True):
                        increment_wear_count(cid)
                        st.toast(f"已记录！『{name}』均价已下降", icon="👕")
                        st.rerun()
                with btn_c2:
                    if st.button("↩️ 减 1 次", key=f"sub_{cid}", use_container_width=True, disabled=(wear_count <= 0)):
                        decrement_wear_count(cid)
                        st.toast(f"已撤消！『{name}』次数已减 1", icon="↩️")
                        st.rerun()

                # 編輯與刪除摺疊選單
                with st.expander("⚙️ 编辑详情 / 刪除"):
                    edit_name = st.text_input("衣服名称", value=name, key=f"name_{cid}")
                    edit_price = st.number_input("购买价格 (¥)", min_value=0.1, step=10.0, value=float(price), key=f"price_{cid}")
                    edit_wear = st.number_input("制订穿着次数", min_value=0, step=1, value=int(wear_count), key=f"wear_{cid}")
                    
                    e_col1, e_col2 = st.columns(2)
                    with e_col1:
                        if st.button("💾 保存修改", key=f"save_{cid}", use_container_width=True):
                            update_clothing(cid, edit_name.strip(), edit_price, edit_wear)
                            st.toast("修改已保存！")
                            st.rerun()
                    with e_col2:
                        if st.button("🗑️ 刪除衣服", key=f"del_{cid}", type="secondary", use_container_width=True):
                            delete_clothing(cid, img_path)
                            st.toast("衣服已从衣柜移除！")
                            st.rerun()

                st.markdown("---")

# ===== 分页 2: 新增衣服 =====
with tab_add:
    st.subheader("新增衣物资料")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        item_name = st.text_input("衣物名称 / 描述", placeholder="例如：米白色针织衫")
    with col_input2:
        item_price = st.number_input("购买价格 (¥)", min_value=0.1, step=10.0, value=200.0)
    
    upload_method = st.radio("选择图片来源", ["📸 手机 / 电脑相机拍照", "📁 本地相册上传"], horizontal=True)
    
    image_data = None
    if "拍照" in upload_method:
        camera_file = st.camera_input("拍照")
        if camera_file:
            image_data = camera_file.getvalue()
    else:
        uploaded_file = st.file_uploader("选择图片", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image_data = uploaded_file.getvalue()
            
    if st.button("💾 储存至衣柜", type="primary", use_container_width=True):
        if not item_name.strip():
            st.error("请输入衣物名称")
        elif image_data is None:
            st.error("请提供衣物照片")
        else:
            add_clothing(item_name.strip(), item_price, image_data)
            st.success("✅ 成功加入衣柜！")
            st.rerun()

# ===== 分页 3: 数据分析 =====
with tab_stats:
    st.subheader("📊 衣柜效益概况")
    items = get_clothes()
    if items:
        total_items = len(items)
        total_cost = sum(x[2] for x in items)
        total_wears = sum(x[3] for x in items)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("衣物总数", f"{total_items} 件")
        c2.metric("总投入金额", f"¥{total_cost:,.1f}")
        c3.metric("累计穿着总次數", f"{total_wears} 次")
        
        worn_items = [x for x in items if x[3] > 0]
        if worn_items:
            best_value = min(worn_items, key=lambda x: x[2] / x[3])
            st.info(f"🏆 **最超值单品**：{best_value[1]}（原价 ¥{best_value[2]}，穿了 {best_value[3]} 次，每次僅需 ¥{best_value[2]/best_value[3]:.2f}）")
    else:
        st.write("尚无统计数据。")

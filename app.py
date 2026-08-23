elif nav_selected == "👚 我的衣橱":
        all_items = get_clothes("全部")
        total_items = len(all_items)
        total_spent = sum(x[2] for x in all_items)

        # 顶部指标 (👕 3  💰 ¥145)
        st.markdown(f"""
        <div class="top-stats">
            <span>👕 {total_items}</span>
            <span>💰 ¥{total_spent:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)

        categories = ["全部"] + get_categories()
        selected_cat = st.pills("分类筛选", categories, default="全部", label_visibility="collapsed")

        target_cat = selected_cat if selected_cat else "全部"
        displayed_items = get_clothes(target_cat)

        st.markdown(f"#### {target_cat} ({len(displayed_items)})")

        if not displayed_items:
            st.info("该分类下暂无衣物，请选择「➕ 新增衣服」上传！")
        else:
            for item in displayed_items:
                cid, name, price, wear_count, img_path, cat, p_year, _, _ = item
                avg_cost = price / wear_count if wear_count > 0 else price
                img_b64 = get_image_base64(img_path)

                # 使用两列布局：左侧为卡片展示，右侧为原生 Streamlit 按钮（防止整页刷新白屏）
                col_card, col_add = st.columns([0.85, 0.15], vertical_alignment="center")

                with col_card:
                    # 点击卡片通过容器响应
                    st.markdown(f"""
                    <div class="app-card" style="margin-bottom:0px; cursor:pointer;">
                        <div class="app-card-left">
                            <img src="data:image/jpeg;base64,{img_b64}" class="app-card-img">
                            <div class="app-card-info">
                                <div class="cpw-price">¥{avg_cost:.2f}/次</div>
                                <div class="sub-info">¥{price:.0f} 已穿 {wear_count} 次</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 隐藏的详情点击区
                    if st.button("查看详情", key=f"det_{cid}", type="tertiary", use_container_width=True):
                        st.session_state.selected_id = cid
                        st.rerun()

                with col_add:
                    # 使用原生按钮替换 HTML <a> 标签，直接在内存中更新并触发局部 rerun
                    if st.button("＋", key=f"add_{cid}", type="primary"):
                        update_wear_count(cid, 1)
                        st.toast("已记录穿着！", icon="👕")
                        st.rerun()

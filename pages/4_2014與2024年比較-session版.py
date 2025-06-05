import streamlit as st
import geemap.foliumap as geemap
import ee
import time
from google.oauth2 import service_account

start_time = time.time()

# GEE 認證
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)

#獲取ee.Image
lst_2014 = st.session_state.lst_2014_image
class_2014 = st.session_state.class_2014_image
lst_2024 = st.session_state.lst_2024_image
class_2024 = st.session_state.class_2024_image

# 獲取視覺化參數
vis_params_temp = st.session_state.vis_params_temp
vis_params_class = st.session_state.vis_params_class
legend_dict = st.session_state.classified_legend_dict


# Streamlit 介面開始
st.title("10年間高雄地區綜整分析比較 - Session State版")
st.markdown("時間範圍：2014 年 7 月與 2024 年 7 月")

    # 地表溫度比較圖
    st.subheader("地表溫度比較圖")
    Map1 = geemap.Map(center=[22.9, 120.6], zoom=9)
    Map1.split_map(
        geemap.ee_tile_layer(lst_2014, vis_params_temp, "2014 LST"),
        geemap.ee_tile_layer(lst_2024, vis_params_temp, "2024 LST")
    )
    Map1.to_streamlit(width=800, height=600)

    # 土地分類比較圖
    st.subheader("土地利用分類比較圖")
    Map2 = geemap.Map(center=[22.9, 120.6], zoom=9)
    Map2.split_map(
        geemap.ee_tile_layer(class_2014, vis_params_class, "2014 Land Cover"),
        geemap.ee_tile_layer(class_2024, vis_params_class, "2024 Land Cover")
    )
    Map2.to_streamlit(width=800, height=600)


end_time = time.time()
elapsed_time = end_time - start_time
st.markdown(f"執行時間: {elapsed_time} 秒")

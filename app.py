import streamlit as st
from datetime import date
import ee
import geemap
import json
import os
from google.oauth2 import service_account

# 從 Streamlit Secrets 讀取 GEE 服務帳戶金鑰 JSON
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]

# 使用 google-auth 進行 GEE 授權
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)

# 初始化 GEE
ee.Initialize(credentials)

st.set_page_config(layout="wide", page_title="期末報告！")

st.title("台灣海岸型城市之都市熱島現象分析")

st.markdown(
    """
    本專案旨在探討台灣西南部海岸型城市（如高雄市）近年來都市熱島現象的空間與時間變化。
    利用 Google Earth Engine 及 Landsat 8 衛星影像，結合地表溫度（LST）計算與時序分析，觀察城市發展對熱島效應的影響。
    """
)

st.title("研究動機")
st.markdown(
    """
    隨著氣候變遷日益嚴峻，加上都市化發展迅速，都市熱島（Urban Heat Island, UHI）效應已成為城市規劃中重要的環境議題。
    台灣作為島嶼型國家，海岸城市如高雄、台南在工業化與人口集中下，可能更易產生熱島現象。
    然而目前針對台灣海岸型城市的長期熱島變化研究仍相對有限，因此本研究希望透過遙測與地理資訊系統，補足此研究空缺。
    """
)

# 設定研究區域
aoi = ee.Geometry.Rectangle([120.075769, 22.484333, 121.021313, 23.285458])

# 產生 Landsat 動態圖
timelapse_gif = geemap.landsat_timelapse(
    aoi,
    out_gif='kaohsiung.gif',
    start_year=2014,
    end_year=2024,
    bands=['Red', 'Green', 'Blue'],
    frames_per_second=5,
    apply_fmask=True,
)

# 顯示 GIF
st.image('kaohsiung.gif', caption='2014-2024 高雄地區 Landsat 動態影像', use_column_width=True)

st.title("研究目的")
st.markdown(
    """
    1. 分析台灣海岸型城市（以高雄為例）近十年來的都市熱島現象變化。
    2. 利用 Landsat 衛星影像與地表溫度推估模型，進行時間序列的熱島空間分布分析。
    3. 探討都市發展與綠地變化對熱島效應的可能影響關係。
    """
)

st.title("研究方法")
st.markdown(
    """
    - **資料來源**：使用 Google Earth Engine 平台，擷取 2014 至 2024 年 Landsat 8 影像。
    - **資料處理**：透過遙測影像預處理（雲遮罩、裁切），計算地表溫度（LST）。
    - **影像分析**：製作每年七月的熱島地圖，進行時間序列分析與變化趨勢探討。
    - **視覺化呈現**：產出動態 GIF，展示十年間熱島效應空間變化。
    """
)

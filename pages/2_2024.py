import streamlit as st
import geemap.foliumap as geemap
import ee
import json
from google.oauth2 import service_account

# --- GEE 認證 ---
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)

# 初始化 GEE (確保只初始化一次)
if not ee.data._initialized:
    ee.Initialize(credentials)

# --- 初始化 Session State 和 GEE 資料處理 ---
# 使用第三個程式碼預期的鍵名來初始化和儲存資料
if 'lst_2024_image' not in st.session_state or st.session_state.lst_2024_image is None:
    st.session_state.lst_2024_image = None # 初始化為 None
if 'class_2024_image' not in st.session_state or st.session_state.class_2024_image is None:
    st.session_state.class_2024_image = None # 初始化為 None

# 初始化通用的視覺化參數，如果它們尚未被設定 (確保與 2014 頁面一致)
if 'vis_params_temp' not in st.session_state:
    st.session_state.vis_params_temp = {
        'min': 10,
        'max': 50,
        'palette': [
            '040274', '0502a3', '0502ce', '0602ff', '307ef3',
            '30c8e2', '3be285', '86e26f', 'b5e22e', 'ffd611',
            'ff8b13', 'ff0000', 'c21301', '911003'
        ]
    }
if 'classified_legend_dict' not in st.session_state:
    st.session_state.classified_legend_dict = {
        'zero': '#3A87AD', 'one': '#D94848', 'two': '#4CAF50', 'three': '#D9B382',
        'four': '#F2D16B', 'five': '#A89F91', 'six': '#61C1E4', 'seven': '#7CB342',
        'eight': '#8E7CC3'
    }
if 'vis_params_class' not in st.session_state:
    st.session_state.vis_params_class = {
        'min': 0,
        'max': len(st.session_state.classified_legend_dict.values()) - 1,
        'palette': list(st.session_state.classified_legend_dict.values())
    }

    # 設定 AOI 與時間範圍
    aoi = ee.Geometry.Rectangle([120.075769, 22.484333, 121.021313, 23.285458])
    startDate = '2024-07-01'
    endDate = '2024-07-31'

    # 資料處理函數
    def applyScaleFactors(image):
        opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
        thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
        return image.addBands(opticalBands, overwrite=True).addBands(thermalBands, overwrite=True)

    def cloudMask(image):
        cloud_shadow_bitmask = (1 << 3)
        cloud_bitmask = (1 << 5)
        qa = image.select('QA_PIXEL')
        mask = qa.bitwiseAnd(cloud_shadow_bitmask).eq(0).And(
                                qa.bitwiseAnd(cloud_bitmask).eq(0))
        return image.updateMask(mask)

    # 建立影像集合
    collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                    .filterBounds(aoi)
                    .filterDate(startDate, endDate))

    image = (collection
            .map(applyScaleFactors)
            .map(cloudMask)
            .median()
            .clip(aoi))

    # 計算 NDVI
    ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')

    ndvi_min = ee.Number(ndvi.reduceRegion(
        reducer=ee.Reducer.min(),
        geometry=aoi,
        scale=30,
        maxPixels=1e9
    ).values().get(0))

    ndvi_max = ee.Number(ndvi.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=aoi,
        scale=30,
        maxPixels=1e9
    ).values().get(0))

    fv = ndvi.subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)) \
        .pow(2).rename("FV")
    em = fv.multiply(0.004).add(0.986).rename("EM")
    thermal = image.select('ST_B10').rename('thermal')

    # Calculate LST
    calculated_lst = thermal.expression(
        '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em))) - 273.15',
        {
            'TB': thermal.select('thermal'),
            'em': em
        }
    ).rename('LST')

    # 將 LST 儲存到 session_state，使用第三個程式碼預期的鍵名
    st.session_state.lst_2024_image = calculated_lst # Changed key

    # 非監督式土地利用分析
    classified_bands = image.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'])

    training001 = classified_bands.sample(
        region=aoi,
        scale=30,
        numPixels=5000,
        seed=0,
        geometries=True
    )

    clusterer_XMeans = ee.Clusterer.wekaXMeans().train(training001)
    calculated_result002 = classified_bands.cluster(clusterer_XMeans)

    # 將分類影像儲存到 session_state，使用第三個程式碼預期的鍵名
    st.session_state.class_2024_image = calculated_result002 # Changed key

# --- Streamlit 介面與地圖顯示 ---
st.title("高雄地區地表溫度分析與土地利用分析")
st.markdown("時間範圍：2024 年 7 月")

# 確保 session_state 中的影像已經存在才能進行地圖顯示
if st.session_state.lst_2024_image is not None and st.session_state.class_2024_image is not None:
    Map = geemap.Map(center=[22.9, 120.6], zoom=9)

    # 從 session_state 取出影像和可視化參數
    lst_2024 = st.session_state.lst_2024_image
    class_2024 = st.session_state.class_2024_image # Changed variable name
    
    vis_params_temp = st.session_state.vis_params_temp
    vis_params_class = st.session_state.vis_params_class
    legend_dict = st.session_state.classified_legend_dict

    left_layer = geemap.ee_tile_layer(lst_2024, vis_params_temp, 'hot island in Kaohsiung (2024)')
    right_layer = geemap.ee_tile_layer(class_2024, vis_params_class, 'wekaXMeans classified land cover (2024)')
    Map.split_map(left_layer, right_layer)
    Map.add_legend(title="土地覆蓋分類", legend_dict=legend_dict) # 為單獨頁面添加圖例

    Map.to_streamlit(width=800, height=600)
else:
    st.info("請等待 2024 年資料載入...")

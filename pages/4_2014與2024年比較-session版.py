import streamlit as st
import geemap.foliumap as geemap
import ee
import json
import timeit
from google.oauth2 import service_account

# GEE 認證
# Read GEE service account key JSON from Streamlit Secrets
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]

# Authenticate GEE using google-auth
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
# Initialize GEE (ensure it's initialized only once per Streamlit app run)
if not ee.data._initialized:
    ee.Initialize(credentials)

# --- Session State 初始化 ---
# Initialize session state variables for GEE images and their visualization parameters.
# This ensures they exist even on the first run and can persist across reruns.
if 'lst_2014_image' not in st.session_state:
    st.session_state.lst_2014_image = None
if 'class_2014_image' not in st.session_state:
    st.session_state.class_2014_image = None
if 'lst_2024_image' not in st.session_state:
    st.session_state.lst_2024_image = None
if 'class_2024_image' not in st.session_state:
    st.session_state.class_2024_image = None

# Visualization parameters and legend are constant, so they can be defined once.
# Storing them in session_state ensures they are readily available and consistent.
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
        'zero': '#3A87AD',
        'one': '#D94848',
        'two': '#4CAF50',
        'three': '#D9B382',
        'four': '#F2D16B',
        'five': '#A89F91',
        'six': '#61C1E4',
        'seven': '#7CB342',
        'eight': '#8E7CC3'
    }
if 'vis_params_class' not in st.session_state:
    palette = list(st.session_state.classified_legend_dict.values())
    st.session_state.vis_params_class = {
        'min': 0,
        'max': len(palette) - 1,
        'palette': palette
    }

# 共用參數 (AOI is constant)
aoi = ee.Geometry.Rectangle([120.075769, 22.484333, 121.021313, 23.285458])

# 共用函數 (Data processing functions)
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

def get_processed_image(date_range):
    collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                    .filterBounds(aoi)
                    .filterDate(date_range[0], date_range[1]))
    image = (collection
             .map(applyScaleFactors)
             .map(cloudMask)
             .median()
             .clip(aoi))
    return image

def calculate_lst(image):
    ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
    # Use maxPixels=1e10 to avoid "Too many pixels" error
    ndvi_min = ee.Number(ndvi.reduceRegion(ee.Reducer.min(), aoi, 30, maxPixels=1e10).values().get(0))
    ndvi_max = ee.Number(ndvi.reduceRegion(ee.Reducer.max(), aoi, 30, maxPixels=1e10).values().get(0))
    fv = ndvi.subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)).pow(2).rename("FV")
    em = fv.multiply(0.004).add(0.986).rename("EM")
    thermal = image.select('ST_B10').rename('thermal')
    lst = thermal.expression(
        '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em))) - 273.15',
        {'TB': thermal.select('thermal'), 'em': em}
    ).rename('LST')
    return lst

def get_classified(image):
    classified_bands = image.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'])
    training = classified_bands.sample(region=aoi, scale=30, numPixels=5000, seed=0, geometries=True)
    clusterer = ee.Clusterer.wekaXMeans().train(training)
    result = classified_bands.cluster(clusterer)
    return result

    # 處理 2014 資料
    image_2014 = get_processed_image(['2014-07-01', '2014-07-31'])
    st.session_state.lst_2014_image = calculate_lst(image_2014)
    st.session_state.class_2014_image = get_classified(image_2014)

    # 處理 2024 資料
    image_2024 = get_processed_image(['2024-07-01', '2024-07-31'])
    st.session_state.lst_2024_image = calculate_lst(image_2024)
    st.session_state.class_2024_image = get_classified(image_2024)

def test():
    L = [i for i in range(100)]  # 生成一個列表
    
# 使用 timeit.timeit 測量 test() 的執行時間
execution_time = timeit.timeit("test()", setup="from __main__ import test", number=100000)

# 確保 session_state 中的影像已經存在才能進行地圖顯示
# Only display the maps if all required images are available in session_state.
if (st.session_state.lst_2014_image is not None and
    st.session_state.class_2014_image is not None and
    st.session_state.lst_2024_image is not None and
    st.session_state.class_2024_image is not None):

    # 從 session_state 取出影像和可視化參數
    lst_2014 = st.session_state.lst_2014_image
    class_2014 = st.session_state.class_2014_image
    lst_2024 = st.session_state.lst_2024_image
    class_2024 = st.session_state.class_2024_image

    vis_params_temp = st.session_state.vis_params_temp
    vis_params_class = st.session_state.vis_params_class
    legend_dict = st.session_state.classified_legend_dict # Retrieve legend dict

    # 第一張圖：地表溫度比較
    Map1 = geemap.Map(center=[22.9, 120.6], zoom=9)
    Map1.split_map(
        geemap.ee_tile_layer(lst_2014, vis_params_temp, "2014 LST"),
        geemap.ee_tile_layer(lst_2024, vis_params_temp, "2024 LST")
    )

    st.subheader("地表溫度比較圖")
    Map1.to_streamlit(width=800, height=600)

    # 第二張圖：土地利用分類比較
    Map2 = geemap.Map(center=[22.9, 120.6], zoom=9)
    Map2.split_map(
        geemap.ee_tile_layer(class_2014, vis_params_class, "2014 Land Cover"),
        geemap.ee_tile_layer(class_2024, vis_params_class, "2024 Land Cover")
    )

    st.subheader("土地利用分類比較圖")
    Map2.to_streamlit(width=800, height=600)

# --- Streamlit 介面與地圖顯示 ---
st.title("10年間高雄地區綜整分析比較-session state")
st.markdown("時間範圍：2014 年 7 月與 2024 年 7 月") # Updated markdown to reflect both years
st.markdown(f"分析時間："{execution_time} "秒")


import streamlit as st
import geemap.foliumap as geemap
import ee
import json
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

# 設定 AOI 與時間範圍
aoi = ee.Geometry.Rectangle([120.075769, 22.484333, 121.021313, 23.285458])
startDate_1 = '2014-07-01'
endDate_1 = '2014-07-31'

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
                .filterDate(startDate_1, endDate_1))

image = (collection
         .map(applyScaleFactors)
         .map(cloudMask)
         .median()
         .clip(aoi))

# 計算 NDVI
ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI_1')

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

fv_1 = ndvi_1.subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)) \
    .pow(2).rename("FV_1")
em_1 = fv.multiply(0.004).add(0.986).rename("EM_1")
thermal_1 = image.select('ST_B10').rename('thermal_1')

lst_1 = thermal.expression(
    '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em_1))) - 273.15',
    {
        'TB': thermal.select('thermal_1'),
        'em_1': em_1
    }
).rename('LST_1')


# 設定 ROI 與時間範圍
roi = ee.Geometry.Rectangle([120.075769, 22.484333, 121.021313, 23.285458])
startDate_2 = '2024-07-01'
endDate_2 = '2024-07-31'

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
                .filterBounds(roi)
                .filterDate(startDate_2, endDate_2))

image = (collection
         .map(applyScaleFactors)
         .map(cloudMask)
         .median()
         .clip(roi))

# 計算 NDVI
ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI_2')

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

fv_2 = ndvi.subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)) \
    .pow(2).rename("FV_2")
em_2 = fv.multiply(0.004).add(0.986).rename("EM_2")
thermal_2 = image.select('ST_B10').rename('thermal_2')

lst_2 = thermal.expression(
    '(TB_2 / (1 + (0.00115 * (TB_2 / 1.438)) * log(em_2))) - 273.15',
    {
        'TB_2': thermal.select('thermal_2'),
        'em_2': em
    }
).rename('LST_2')

# 地圖視覺化參數

vis_params_001 = {
    'min': 10,
    'max': 50,
    'palette': [
        '040274', '0502a3', '0502ce', '0602ff', '307ef3',
        '30c8e2', '3be285', '86e26f', 'b5e22e', 'ffd611',
        'ff8b13', 'ff0000', 'c21301', '911003'
    ]
}



Map = geemap.Map(center=[22.9, 120.6], zoom=9)
left_layer = geemap.ee_tile_layer(lst_1,vis_params_001 , 'hot island in Kaohsiung2014')
right_layer = geemap.ee_tile_layer(lst_2,vis_params_001 , 'hot island in Kaohsiung2024')
Map.split_map(left_layer, right_layer)

# Streamlit 介面
st.title("高雄地區 NDVI 與地表溫度分析")
st.markdown("時間範圍：2014 年 7 月")
Map.to_streamlit(width=800, height=600)

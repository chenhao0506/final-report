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

lst = thermal.expression(
    '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em))) - 273.15',
    {
        'TB': thermal.select('thermal'),
        'em': em
    }
).rename('LST')

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



#非監督式土地利用分析

# 選擇分類用波段
classified_bands = image.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'])

# 抽樣產生訓練資料
training001 = classified_bands.sample(
    region=aoi,
    scale=30,
    numPixels=5000,
    seed=0,
    geometries=True
)

# 訓練分類器並分類
clusterer_XMeans = ee.Clusterer.wekaXMeans().train(training001)
result002 = classified_bands.cluster(clusterer_XMeans)

legend_dict = {
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

palette = list(legend_dict.values())


vis_params_002 = {
    'min': 0,
    'max': len(palette) - 1,
    'palette': palette
}


Map = geemap.Map(center=[22.9, 120.6], zoom=9)
left_layer = geemap.ee_tile_layer(lst,vis_params_001 , 'hot island in Kaohsiung')
right_layer = geemap.ee_tile_layer(result002,vis_params_002 , 'wekaXMeans classified land cover')
Map.split_map(left_layer, right_layer)

# Streamlit 介面
st.title("高雄地區 NDVI 與地表溫度分析")
st.markdown("時間範圍：2024 年 7 月")
Map.to_streamlit(width=800, height=600)

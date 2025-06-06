import streamlit as st
import geemap.foliumap as geemap
import ee
import json
import time
from google.oauth2 import service_account

start_time = time.time()

# GEE 認證
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials)

# 共用參數
aoi = ee.Geometry.Rectangle([120.075769, 22.484333, 121.021313, 23.285458])
vis_params_temp = {
    'min': 10,
    'max': 50,
    'palette': [
        '040274', '0502a3', '0502ce', '0602ff', '307ef3',
        '30c8e2', '3be285', '86e26f', 'b5e22e', 'ffd611',
        'ff8b13', 'ff0000', 'c21301', '911003'
    ]
}
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
vis_params_class = {
    'min': 0,
    'max': len(palette) - 1,
    'palette': palette
}

# 共用函數
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
    ndvi_min = ee.Number(ndvi.reduceRegion(ee.Reducer.min(), aoi, 30,maxPixels = 1e10).values().get(0))
    ndvi_max = ee.Number(ndvi.reduceRegion(ee.Reducer.max(), aoi, 30,maxPixels = 1e10).values().get(0))
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
lst_2014 = calculate_lst(image_2014)
class_2014 = get_classified(image_2014)

# 處理 2024 資料
image_2024 = get_processed_image(['2024-07-01', '2024-07-31'])
lst_2024 = calculate_lst(image_2024)
class_2024 = get_classified(image_2024)

    # Streamlit 介面與地圖顯示
st.title("10年間高雄地區綜整分析比較-重做版")
st.markdown("時間範圍：2014 年 7 月與 2024 年 7 月") # Updated markdown to reflect both years

# 第一張圖：地表溫度比較
Map1 = geemap.Map(center=[22.9, 120.6], zoom=9)
Map1.split_map(
    geemap.ee_tile_layer(lst_2014, vis_params_temp, "2014 LST"),
    geemap.ee_tile_layer(lst_2024, vis_params_temp, "2024 LST")
)

# 第二張圖：土地利用分類比較
Map2 = geemap.Map(center=[22.9, 120.6], zoom=9)
Map2.split_map(
    geemap.ee_tile_layer(class_2014, vis_params_class, "2014 Land Cover"),
    geemap.ee_tile_layer(class_2024, vis_params_class, "2024 Land Cover")
)

st.subheader("地表溫度比較圖")
Map1.to_streamlit(width=800, height=600)

st.subheader("土地利用分類比較圖")
Map2.to_streamlit(width=800, height=600)

end_time = time.time()
elapsed_time = end_time - start_time
st.markdown(f"執行時間: {elapsed_time} 秒")

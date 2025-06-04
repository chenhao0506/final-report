import streamlit as st
import geemap.foliumap as geemap
import ee
import json
from google.oauth2 import service_account

# 初始化 GEE 驗證
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials)

# 區域與時間設定
aoi = ee.Geometry.Rectangle([120.075769, 22.484333, 121.021313, 23.285458])
dates = {
    "2014": ("2014-07-01", "2014-07-31"),
    "2024": ("2024-07-01", "2024-07-31")
}

# 共用函數
def applyScaleFactors(image):
    optical = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    thermal = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    return image.addBands(optical, overwrite=True).addBands(thermal, overwrite=True)

def cloudMask(image):
    cloud = (1 << 5)
    qa = image.select('QA_PIXEL')
    mask = qa.bitwiseAnd(cloud).eq(0)
    return image.updateMask(mask)

def get_LST_and_NDVI(start, end):
    col = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
           .filterBounds(aoi)
           .filterDate(start, end)
           .map(applyScaleFactors)
           .map(cloudMask))

    img = col.median().clip(aoi)
    ndvi = img.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')

    ndvi_min = ee.Number(ndvi.reduceRegion(ee.Reducer.min(), aoi, 30).values().get(0))
    ndvi_max = ee.Number(ndvi.reduceRegion(ee.Reducer.max(), aoi, 30).values().get(0))
    fv = ndvi.subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)).pow(2).rename("FV")
    em = fv.multiply(0.004).add(0.986).rename("EM")
    thermal = img.select('ST_B10')

    lst = thermal.expression(
        '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em))) - 273.15',
        {'TB': thermal, 'em': em}
    ).rename('LST')

    return img, ndvi, lst.unmask(0)

def classify_unsupervised(image):
    bands = image.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'])
    samples = bands.sample(region=aoi, scale=30, numPixels=5000, seed=0, geometries=True)
    clusterer = ee.Clusterer.wekaXMeans().train(samples)
    result = bands.cluster(clusterer)
    return result

# 視覺化參數
lst_vis = {
    'min': 10,
    'max': 50,
    'palette': ['040274', '0502a3', '0502ce', '0602ff', '307ef3',
                '30c8e2', '3be285', '86e26f', 'b5e22e', 'ffd611',
                'ff8b13', 'ff0000', 'c21301', '911003']
}

landuse_palette = [
    '#3A87AD', '#D94848', '#4CAF50', '#D9B382', '#F2D16B',
    '#A89F91', '#61C1E4', '#7CB342', '#8E7CC3'
]
landuse_vis = {
    'min': 0,
    'max': len(landuse_palette) - 1,
    'palette': landuse_palette
}

# 資料準備
img_2014, ndvi_2014, lst_2014 = get_LST_and_NDVI(*dates["2014"])
img_2024, ndvi_2024, lst_2024 = get_LST_and_NDVI(*dates["2024"])

lu_2014 = classify_unsupervised(img_2014)
lu_2024 = classify_unsupervised(img_2024)

# Streamlit 介面
st.title("高雄地區遙測分析系統")
tab1, tab2 = st.tabs(["地表溫度分析", "土地利用分析"])

with tab1:
    st.subheader("地表溫度比較 (LST)")
    st.markdown("時間範圍：**2014 年 7 月** vs **2024 年 7 月**")
    map1 = geemap.Map(center=[22.9, 120.6], zoom=9)
    map1.split_map(
        geemap.ee_tile_layer(lst_2014, lst_vis, 'LST 2014'),
        geemap.ee_tile_layer(lst_2024, lst_vis, 'LST 2024')
    )
    map1.to_streamlit(width=800, height=600)

with tab2:
    st.subheader("非監督式土地利用分類")
    st.markdown("時間範圍：**2014 年 7 月** vs **2024 年 7 月**")
    map2 = geemap.Map(center=[22.9, 120.6], zoom=9)
    map2.split_map(
        geemap.ee_tile_layer(lu_2014, landuse_vis, '土地利用 2014'),
        geemap.ee_tile_layer(lu_2024, landuse_vis, '土地利用 2024')
    )
    map2.to_streamlit(width=800, height=600)

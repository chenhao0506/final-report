import streamlit as st
import geemap.foliumap as geemap
import ee
from google.oauth2 import service_account

# 初始化 GEE
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

# 工具函數
def applyScaleFactors(image):
    optical = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    thermal = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    return image.addBands(optical, overwrite=True).addBands(thermal, overwrite=True)

def cloudMask(image):
    cloud = (1 << 5)
    qa = image.select('QA_PIXEL')
    mask = qa.bitwiseAnd(cloud).eq(0)
    return image.updateMask(mask)

def get_LST(start, end):
    collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                  .filterBounds(aoi)
                  .filterDate(start, end)
                  .map(applyScaleFactors)
                  .map(cloudMask))

    img = collection.median().clip(aoi)
    thermal = img.select('ST_B10')

    # 採用固定 emissivity（避免 NDVI 導致錯誤），保守估計都市地區
    emissivity = ee.Image.constant(0.97).clip(aoi)

    lst = thermal.expression(
        '(TB / (1 + (0.00115 * (TB / 1.438)) * log(e))) - 273.15',
        {'TB': thermal, 'e': emissivity}
    ).rename("LST")

    lst = lst.updateMask(lst.gt(10).And(lst.lt(50)))  # 合理範圍過濾
    return lst

# LST 色彩視覺參數
lst_vis = {
    'min': 10,
    'max': 50,
    'palette': ['040274', '0502a3', '0502ce', '0602ff', '307ef3',
                '30c8e2', '3be285', '86e26f', 'b5e22e', 'ffd611',
                'ff8b13', 'ff0000', 'c21301', '911003']
}

# 產生 2014 與 2024 的地表溫度
lst_2014 = get_LST(*dates["2014"])
lst_2024 = get_LST(*dates["2024"])

# Streamlit UI
st.title("高雄地區地表溫度比較（2014 vs 2024）")
st.markdown("下方展示 Landsat 衛星於 2014 年與 2024 年 7 月的地表溫度圖層，使用固定發射率 0.97 計算")

# 地圖 1：2014 年
st.subheader("2014 年 7 月地表溫度")
m1 = geemap.Map(center=[22.9, 120.6], zoom=9)
m1.addLayer(lst_2014, lst_vis, "LST 2014")
m1.to_streamlit(width=800, height=500)

# 地圖 2：2024 年
st.subheader("2024 年 7 月地表溫度")
m2 = geemap.Map(center=[22.9, 120.6], zoom=9)
m2.addLayer(lst_2024, lst_vis, "LST 2024")
m2.to_streamlit(width=800, height=500)

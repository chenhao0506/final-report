import ee
ee.Authenticate()
ee.Initialize(project="ee-s12430230")

!pip install geemap earthengine-api

import geemap
aoi = ee.Geometry.Rectangle([120.075769, 22.484333, 121.021313, 23.285458])

Map = geemap.Map()
Map.addLayer(aoi, {}, 'AOI - Kaohsiung');
Map.centerObject(aoi, 9);
Map

startDate = '2024-07-01'
endDate = '2024-07-31'

#應用縮放因子
def applyScaleFactors(image):
    # Scale and offset values for optical bands
    opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)

    # Scale and offset values for thermal bands
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)

    # Add scaled bands to the original image
    image = image.addBands(opticalBands, overwrite=True)
    image = image.addBands(thermalBands, overwrite=True)

    return image

#應用 CloudMask
def cloudMask(image):
    # 定義雲影和雲的 bit mask（bit 3 和 bit 5）
    cloud_shadow_bitmask = (1 << 3)
    cloud_bitmask = (1 << 5)

    # 選擇 QA_PIXEL 品質評估波段
    qa = image.select('QA_PIXEL')

    # 建立遮罩條件（bit 3 和 bit 5 都等於 0 表示無雲也無雲影）
    mask = qa.bitwiseAnd(cloud_shadow_bitmask).eq(0).And(
           qa.bitwiseAnd(cloud_bitmask).eq(0))

    # 將原始影像中被雲或雲影遮擋的像素遮掉
    return image.updateMask(mask)

collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                .filterBounds(aoi)
                .filterDate(startDate, endDate))
print('Image count:', collection.size().getInfo())

#導入 Landsat 8 影像
image = (collection
         .map(applyScaleFactors)
         .map(cloudMask)
         .median()
         .clip(aoi))

# 設定真彩色顯示參數（432 = 紅、綠、藍）
visualization = {
    'bands': ['SR_B4', 'SR_B3', 'SR_B2'],
    'min': 0.0,
    'max': 0.3
}

# 顯示影像
Map = geemap.Map()
Map.centerObject(aoi, 9)
Map.addLayer(image, visualization, 'True Color 432')
Map

# 計算 NDVI
ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')

# NDVI 顯示參數
ndvi_vis = {
    'min': -1,
    'max': 1,
    'palette': ['blue', 'white', 'green']
}

# 加到地圖上
Map.addLayer(ndvi, ndvi_vis, 'NDVI - Kaohsiung')
Map

# 計算 NDVI 最小值
ndvi_min = ee.Number(ndvi.reduceRegion(
    reducer=ee.Reducer.min(),
    geometry=aoi,
    scale=30,
    maxPixels=1e9
).values().get(0))

# 計算 NDVI 最大值
ndvi_max = ee.Number(ndvi.reduceRegion(
    reducer=ee.Reducer.max(),
    geometry=aoi,
    scale=30,
    maxPixels=1e9
).values().get(0))

# 印出 NDVI 最小與最大值
print('NDVI 最小值:', ndvi_min.getInfo())
print('NDVI 最大值:', ndvi_max.getInfo())

# 計算植被覆蓋率（FV）
fv = ndvi.subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)) \
    .pow(2).rename("FV")

# 計算地表發射率（EM）
em = fv.multiply(0.004).add(0.986).rename("EM")
print(fv.getInfo())
print(em.getInfo())

# 選擇熱紅外波段並重新命名為 thermal
thermal = image.select('ST_B10').rename('thermal')

# 使用 Expression 計算地表溫度 (LST)
# LST 公式: (TB / (1 + (λ * (TB / 1.438)) * ln(em))) - 273.15
# 其中 λ（波長）為 10.8μm，這裡簡化使用 0.00115（常見 Landsat TIRS λ = 10.8μm）

lst = thermal.expression(
    '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em))) - 273.15',
    {
        'TB': thermal.select('thermal'),
        'em': em
    }
).rename('LST Yogyakarta 2023')

# LST 視覺化參數
lst_vis = {
    'min': 18.47,
    'max': 42.86,
    'palette': [
        '040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6',
        '0602ff', '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef',
        '3be285', '3ff38f', '86e26f', '3ae237', 'b5e22e', 'd6e21f',
        'fff705', 'ffd611', 'ffb613', 'ff8b13', 'ff6e08', 'ff500d',
        'ff0000', 'de0101', 'c21301', 'a71001', '911003'
    ]
}

# 加到地圖上顯示
Map.addLayer(lst, lst_vis, 'Land Surface Temperature 2023')
Map

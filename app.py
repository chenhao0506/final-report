import streamlit as st
from datetime import date
import geemap

st.set_page_config(layout="wide", page_title="期末報告！")

st.title("台灣海岸型城市之都市熱島現象分析")

st.markdown(
    """
   台灣海岸型城市之都市熱島現象分析
    """
)

st.title("研究動機")

st.markdown(  
    """
    這裡要打研究動機
    """
)

my_Map = geemap.Map()
aoi = ee.Geometry.Rectangle([121.1165, 24.8034, 121.3427, 25.1027])

my_timelapse = geemap.landsat_timelapse(
    aoi,
    out_gif='kaohsiung.gif',
    start_year=2014,
    end_year=2024,
    bands=['Red', 'Green', 'Blue'],
    frames_per_second=5,
    apply_fmask=True,
)
geemap.show_image(my_timelapse)

st.title("研究目的")

st.markdown(  
    """
    這裡要打研究目的
    """
)

st.title("研究方法")
st.markdown( 
    """
    這裡要打研究方法
    """
)

#This is the new homepage

#cd "C:\Users\BNH0SRP\Call Center Project\Call_Center_Dashboard"
#python -m streamlit run dashboard.py

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import streamlit as st
from datetime import date
import pandas as pd
import plotly.express as px

from shared import (
    page_setup,
    global_sidebar,
    table_call_data_preview,
    bar_v1)
page_setup()
st.title("Dashboard Home Page")
st.markdown("""Use this page to upload data and canfigure performance targets.""")


def initialize_session_state():
    if "call_df_original" not in st.session_state:
        st.session_state["call_df_original"] = None
    if "call_df_filtered" not in st.session_state:
        st.session_state["call_df_filtered"] = None
    if "agent_map_custom" not in st.session_state:
        st.session_state["agent_map_custom"] = None
    if "smc_df_original" not in st.session_state:
        st.session_state["smc_df_original"] = None

    #POA settings
    if "poa_conventional_defects" not in st.session_state:
        st.session_state["poa_conventional_defects"] = 5.0
    
    if "poa_tsg_defects" not in st.session_state:
        st.session_state["poa_tsg_defects"] = 5.0   
    if "poa_base_defects" not in st.session_state:
        st.session_state["poa_base_defects"] = 5.0
    if "poa_facility_sfr_wait_time" not in st.session_state:
        st.session_state["poa_facility_sfr_wait_time"] = 90.0
    if "poa_automation_wait_time" not in st.session_state:
        st.session_state["poa_automation_wait_time"] = 90.0
    if "poa_conventional_mttr" not in st.session_state:
        st.session_state["poa_conventional_mttr"] = 2.0
    if "poa_automation_mttr" not in st.session_state:
        st.session_state["poa_automation_mttr"] = 1.0

   

initialize_session_state()




# Generate Sidebar
if st.session_state.get("call_df_original") is not None:
    global_sidebar() #this is the new filtering logic
else:
    st.sidebar.info("Upload call data to activate filters")
# Main Page Layout
st.divider()

c1, c2 = st.columns(2)

with c1:
    st.subheader("Upload Call Data")
    uploaded_file = st.file_uploader(
        "Upload Digium Data",
        type=["csv"],
        key="call_data_uploader"
    )
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        #st.session_state["call_df_original"] = process_uploaded_call_file(df)
        st.session_state["call_df_filtered"] = df.copy()
        st.success("Call data uploaded successfully!")
        st.session_state["call_df_filtered"] = df.copy()
        table_call_data_preview()
    mapping_ext_file = st.file_uploader("Upload Extension Mapping File", type=["csv"], key="ext_mapping_uploader")

    if mapping_ext_file is not None:
        ext_df = pd.read_csv(mapping_ext_file)
        st.session_state["agent_map_custom"] = ext_df
        st.success("Extension mapping file uploaded successfully!")
        st.write("Extension Mapping Data:")
        st.dataframe(ext_df)
    else:
        pass
    
# pages/1_Performance_Report.py 
import streamlit as st
import pandas as pd
from datetime import datetime
from utils import (
    create_global_sidebar,
    load_digium_kpi,
    chart_calls_by_category,
    generate_performance_pdf,
    display_active_filters,
    chart_calls_by_category,
    donut_hold_time_breakdown,
    top_3_hold_times,
    auto_calls_line_graph,
    auto_avg_resolution_bar,
    auto_percent_resolved,
    shifts,
    poa_table,
    top_3_talk_times,
)
from smc import smc_stats, initialize_smc_poa, top_4_inc
# --- Page Setup ---
 
  
st.title("Performance Report")
# Use the global sidebar to get the date range
create_global_sidebar()
# --- Data Loading and Validation ---
if 'df_filtered' not in st.session_state or st.session_state['df_filtered'] is None or st.session_state['df_filtered'].empty:
    st.warning("Please upload and filter data on the Home page to view this report.")
    st.stop()
df = st.session_state['df_filtered']

# Display the active filters for context
display_active_filters()
# Ensure start_date and end_date are datetime objects
if 'filter_selections' in st.session_state and "Date Range" in st.session_state['filter_selections']:
    date_range = st.session_state['filter_selections']["Date Range"]
    # Expecting date_range to be a tuple/list like (start_date, end_date)
    start_date, end_date = date_range
    # Convert to datetime if they are strings
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    st.subheader(f"MHE Automated Systems from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
else:
    st.error("Date Range filter is missing. Please set it on the Home page.")
    st.stop()
st.markdown("This page provides the key performance indicators for Dwayne's weekly summary.")



# --- PDF Export Button ---
# We calculate all necessary data and figures *before* displaying them
# so they can be passed to the PDF generator.

# 1. Calculate KPIs

initialize_smc_poa()
poa_table(df)



st.divider()

# --- Display Report on Page ---
st.header("Call Center Metrics")
load_digium_kpi(df) 

st.divider()

#st.header("Call Center Metrics")
c1, c2, c3 = st.columns(3)
category_fig = chart_calls_by_category(df)
with c1:
    if category_fig:
        st.plotly_chart(category_fig, use_container_width=True)
with c2:
    donut_hold_time_breakdown(df, "Top 3 Longest Hold Times (min.)")
            
with c3:
    #donut_talk_time_breakdown(df, "Top 3 Longest Call Times (min.)")
    with st.expander("Summary", expanded=True):
           #S st.write("**Top 4 Most Frequent Issues**" )
            #st.warning("Need SMC integration")
            top_4_inc()
            top_3_talk_times(df)
            top_3_hold_times(df)
    
'''
st.divider()
d1, d2, d3, d4 = st.columns(4)
with d1:
    auto_percent_resolved(df)
with d2:   
    shifts(df)
with d3:
    auto_calls_line_graph(df)
with d4:
    auto_avg_resolution_bar(df)
'''

st.divider()
smc_stats()
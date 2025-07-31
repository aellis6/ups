# pages/2_Operations_Dashboard.py
import streamlit as st
from datetime import datetime
from utils import (
    create_global_sidebar,
    chart_calls_by_category,
    donut_hold_time_breakdown,
    display_active_filters,
    hold_top3_shift,
    calls_by_day_bar,
    gt_2_traverse,
)
# --- Page Setup ---
st.set_page_config( 
    page_title="Operations Dashboard", 
    layout="wide", 
    page_icon="images/upslogo.png" 
)
st.title("Operations Dashboard")
if 'filter_selections' in st.session_state and "Date Range" in st.session_state['filter_selections']:
    start_date, end_date = st.session_state['filter_selections']['Date Range']
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    st.subheader(f"Report for {start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}")
st.markdown("Internal call handling and routing performance.")
create_global_sidebar()
# --- Data Loading and Validation ---
if 'df_filtered' not in st.session_state or st.session_state['df_filtered'] is None:
    st.warning("Please upload and filter data on the Home page to view this report.")
    st.stop()
df = st.session_state['df_filtered']
# Display the active filters for context
if df.empty:
        st.warning("No data loaded yet. Please upload a file on the Home page.")
        st.stop()
display_active_filters()
st.divider()
# --- Tab-Based Layout ---
tab1, tab2 = st.tabs(["Automation Focus", "Other Call Types (CBRE, Managers)"])
with tab1:
    st.header("Automation Performance")

    automation_df = df[df['Call Category'].str.contains('Automation', na=False)]
    if automation_df.empty:
        st.info("No Automation data for the selected filters.")
    
    else:
        st.markdown(f"Found **{len(automation_df)}** automation-related calls.")
        # Add charts and metrics specific to the automation_df
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Automation Calls", len(automation_df))
            
            # Count of returned automation calls and how many of those were abandoned
            returned_calls = automation_df[automation_df['From'].str.contains("return", case=False, na=False)]
            # Abandoned calls are when the value in the cell shows TRUE (case-insensitive)
            abandoned_count = returned_calls['Abandoned'].astype(str).str.lower().eq('true').sum()
            st.metric("Returned Calls Abandoned", abandoned_count)
            st.markdown(f"Call returned from CBRE: **{len(returned_calls)}**  \nReturned and abandoned: **{abandoned_count}**")
            st.metric("Avg. Hold Time (m)", f"{automation_df['Hold Time (s)'].mean() / 60:.2f}")
            calls_by_day_bar()
            
            df = st.session_state['df_filtered']
            hold_top3_shift(df)
            
        
        
        
        
        
        with c2:
            hold_donut = donut_hold_time_breakdown(automation_df, "Automation Hold Time Breakdown")
            # Only plot if the function does not already display the chart
            if hold_donut is not None:
                st.plotly_chart(hold_donut, use_container_width=True)
    
        gt_2_traverse()

#st.info("More data here will include a way to see what calls led to longer hold times, what calls have longest MMTR, breakdown of SLAW trends, link call to ticket data")
with tab2:
    st.header("Other Call Type Performance")
    
    other_df = df[~df['Call Category'].str.strip().str.contains('Automation', case=False, na=False)]
    st.write(df['Call Category'].value_counts())
    st.markdown(f"Found **{len(other_df)}** other calls (CBRE, Managers, etc.).")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total Other Calls", len(other_df))
        st.metric("Avg. Hold Time (s)", f"{other_df['Hold Time (s)'].mean():.2f}")
    with c2:
        other_pie = chart_calls_by_category(other_df)
        if other_pie:
            st.plotly_chart(other_pie, use_container_width=True)
        else:
            st.info("No data for other call types in the selected filters.")
    st.subheader("Mark's 6-Month Hold Time Analysis")
    st.info("1. Use the `Call Data Retrieval Tool.exe` app after configuring the config.ini file to have 6 months of historical data.  \n " \
            "2. Upload CSV file on `Home` page  \n"
            "3. View results here:")
    df = st.session_state['df_filtered']
    if df.empty:
        st.info("No data available for hold time analysis.")
    else:
        all_hold_donut = donut_hold_time_breakdown(df, "Hold Time Breakdown (All Calls)")
        if all_hold_donut is not None:
            st.plotly_chart(all_hold_donut, use_container_width=True)
        hold_top3_shift(df)
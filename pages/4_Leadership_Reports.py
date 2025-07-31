import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from utils import (
    create_global_sidebar,
    display_active_filters,
    chart_calls_by_category,
    donut_hold_time_breakdown,
    auto_avg_resolution_bar,
    top_3_hold_times,
    generate_performance_pdf,
    dwayne_YTD_avg_hold,
    dwayne_YTD_top_avg_hold,
    auto_call_hold_time_by_shift,
    hold_top3_shift,
    auto_call_hold_time_by_shift,
    dwayne_YTD_top_avg_hold2,
)
from smc import (
    pct_resolved_3rd_lvl,
    pct_resolved_in_7_days,
    total_defects_pct,
    region_bar,
    support_lvl_table,
    defects_table,
    )

# --- Page Setup ---
st.set_page_config(
    page_title="Export Report",
    layout="wide",
    page_icon="images/upslogo.png"
)

st.title("Exportable Weekly PDF Summary")
create_global_sidebar()

# --- Data Validation ---
if 'df_filtered' not in st.session_state or st.session_state['df_filtered'].empty:
    st.warning("Please upload and filter data on the Home page to view this report.")
    st.stop()

df = st.session_state['df_filtered']

# --- Filter Context ---
display_active_filters()

# --- Header Section ---
if 'filter_selections' in st.session_state and "Date Range" in st.session_state['filter_selections']:
    start_date, end_date = st.session_state['filter_selections']['Date Range']
    # Ensure dates are datetime objects for formatting
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    st.subheader(f"Report for {start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}")
else:
    st.error("Date Range filter is missing. Please set it on the Home page.")
    st.stop()

# --- KPI Gauges with POA ---
#table here of the counts of calls broken into Automation, SF< other, vendor, cbre total, and sum total

#pie chart of call breakdown
# 
# #table of hold time by shift
 
#st.markdown("### POA Gauges")
# Reduce vertical gap between the subheader and the gauges row, and between gauges and divider
st.markdown(
    """
    <style>
    .report-gap { margin-bottom: -1.5rem; }
    .block-container { padding-top: 1rem !important; }
    .stHorizontalBlock { margin-bottom: -1.5rem !important; }
    .stDivider { margin-top: -2rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="report-gap"></div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6, gap="small")
comments_list = []

# --- Metric Calculations & Gauge Generation ---
total_calls = df['Call ID'].nunique()

#with c0:
#   pass
#   UPS_COLORS = [
#    "#fbbb06", "#1d65b3", "#5c5c5c", "#94c4ec", "#340404", "#A56f15",
#]
#   automation_df = df[df['Call Category'].str.contains('Automation', na=False)]
#   # Total Call Summary
   #table with columns for call type, and column for count
    
   #call types are: Automation, SFR, Other, Vendor, CBRE, Total
 #  call_types = ['Automation', 'SFR', 'Other', 'Vendor', 'CBRE Total', 'Total', 'sum']
 #  call_counts = [
       
  #     len(automation_df),
   #    df[df['Call Category'] == 'CBRE SFR']['Call ID'].nunique(),
    #   df[df['Call Category'] == 'CBRE Legacy']['Call ID'].nunique(),
##      df[df['Call Category'] == 'CBRE SFR']['Call ID'].nunique() + df[df['Call Category'] == 'CBRE Legacy']['Call ID'].nunique(),
    #sum total
  #  sum([
#        len(automation_df),
 #       df[df['Call Category'] == 'CBRE SFR']['Call ID'].nunique(),
  #      df[df['Call Category'] == 'CBRE Legacy']['Call ID'].nunique(),
   #     df[df['Call Category'] == 'CBRE Legacy']['Call ID'].nunique(),
    #]),

#       total_calls,


#    #display counts in table
 #  df_summary = pd.DataFrame({'Call Type': call_types, 'Call Count': call_counts})
  # st.table(df_summary.set_index('Call Type'))
   #also have a pie chart with this data from the table
   

#with c00:
 #pass
   #fig_pie = go.Figure(data=[go.Pie(labels=call_types, values=call_counts)])
  # #use ups colors
 #  fig_pie.update_traces(marker=dict(colors=UPS_COLORS))
  # fig_pie.update_layout(title_text="Total Call Breakdown by Type")
   #st.plotly_chart(fig_pie, use_container_width=True)

with c1:
    poa = 2
    avg_hold_time_min = pd.to_numeric(df['Hold Time (s)'], errors='coerce').mean() / 60
    color = "green" if avg_hold_time_min <= 2 else "red" if avg_hold_time_min <= 3 else "red"
    if color == "red":
        comments_list.append(f"❗ **Avg Hold Time:** Exceeds 2 minutes ({avg_hold_time_min:.1f} min).")
    fig_hold = go.Figure(go.Indicator(
        mode="gauge+number", value=avg_hold_time_min,
        title={'text': "Avg Hold Time (min) - Target < 2 min", 'font': {'size': 12}},
        gauge={
            'axis': {'range': [0, 5]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 1], 'color': "gray"},
                {'range': [1, 2], 'color': "darkgray"},
                {'range': [2, 5], 'color': "lightgrey"}
            ],
            'threshold': {
                'line': {'color': "#005DAA", 'width': 4},
                'thickness': 0.75,
                'value': poa
            }
        }
    ))
    fig_hold.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_hold, use_container_width=True)

# C2: Avg Time to Resolution (min)
with c2:
    poa = 90
    answered_pct = (df['Hold Time (s)'] < 300).sum() / len(df) * 100
    color = "green" if answered_pct >= 90 else "red" if answered_pct >= 80 else "red"
    if color == "red":
        comments_list.append("❗ **% Answered < 5min:** Less than 80% of calls were answered in under 5 minutes.")
    fig_answered = go.Figure(go.Indicator(
        mode="gauge+number",
        value=answered_pct,
        title={"text": "% Answered < 5min- Target > 90 %}", 'font': {'size': 12}},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': color},
            'steps': [{'range': [0, 80], 'color': "grey"},
                        {'range': [80, 90], 'color': "darkgrey"},
                        {'range': [90, 100], 'color': "lightgrey"}],
        'threshold': {'line': {'color': "#005DAA", 'width': 4},
                        'thickness': 0.75, 'value': poa }}
    ))
    fig_answered.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_answered, use_container_width=True)

# C3: Avg Hold Time (min)
with c3:
    poa = 3
    auto_mttr_min = st.session_state.smc_auto_mttr
    color = "green" if auto_mttr_min <= 30 else "red" if auto_mttr_min <= 60 else "red"
    if color == "red":
        comments_list.append(f"❗ **Avg Time to Resolution:** Exceeds 60 minutes ({auto_mttr_min:.1f} min).")
    fig_resolution = go.Figure(go.Indicator(
        mode="gauge+number", value=auto_mttr_min,
        title={'text': "Avg Time to Resolution (min) - Target < 3 min", 'font': {'size': 12}},
        gauge={
            'axis': {'range': [0, 5]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 1], 'color': "gray"},
                {'range': [1, 2], 'color': "darkgray"},
                {'range': [2, 5], 'color': "lightgrey"}
            ],
            'threshold': {
                'line': {'color': "#005DAA", 'width': 4},
                'thickness': 0.75,
                'value': poa
            }
        }))
    fig_resolution.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_resolution, use_container_width=True)

# C4: % Resolved by 3rd Level
with c4:
    poa = 90
    pct_resolved_3rd = int(pct_resolved_3rd_lvl())
    if pct_resolved_3rd is None:
        pct_resolved_3rd = 0
    color = "green" if pct_resolved_3rd >= 90 else "red" if pct_resolved_3rd >= 80 else "red"
    if color == "red":
        comments_list.append("❗ **% Resolved by 3rd Level:** Below 80%.")
    fig_3rd_lvl = go.Figure(go.Indicator(
        mode="gauge+number", value=pct_resolved_3rd,
        title={'text': "% Resolved by 3rd Lvl - Target > 90%", 'font': {'size': 12}},
        gauge={'axis': {'range': [0, 100]},
        'bar': {'color': color},
        'steps': [{'range': [0, 50], 'color': "grey"},
                    {'range': [50, 75], 'color': "darkgray"},
                    {'range': [75, 100], 'color': "lightgray"}],
        'threshold': {'line': {'color': "#005DAA", 'width': 4},
                        'thickness': 0.75, 'value': poa }}))
    fig_3rd_lvl.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_3rd_lvl, use_container_width=True)

# C5: % Cases Resolved < 7 days
with c5:
    pct_resolved_7_days = pct_resolved_in_7_days()
    if pct_resolved_7_days is None:
        pct_resolved_7_days = 0
    poa = 95
    color = "green" if pct_resolved_7_days >= 95 else "red" if pct_resolved_7_days >= 90 else "red"
    if color == "red":
        comments_list.append("❗ **% Resolved < 7 Days:** Below 90%.")
    fig_7_days = go.Figure(go.Indicator(
        mode="gauge+number", value=pct_resolved_7_days,
        title={'text': "% Resolved < 7 Days - Target > 95%", 'font': {'size': 12}},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': color},
            'steps': [{'range': [0, 90], 'color': "grey"},
                        {'range': [90, 95], 'color': "darkgrey"},
                        {'range': [95, 100], 'color': "lightgrey"}],
                'threshold': {'line': {'color': "#005DAA", 'width': 4},
                            'thickness': 0.75, 'value': poa}}
    ))
    fig_7_days.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_7_days, use_container_width=True)

# C6: Total Defects %
with c6:
    defects_pct_value = total_defects_pct()
    try:
        defects_pct_value = float(defects_pct_value)
    except (TypeError, ValueError):
        defects_pct_value = 0
    color = "green" if defects_pct_value < 5 else "yellow" if defects_pct_value < 10 else "red"
    if color == "red":
        comments_list.append("❗ **Total Defects %:** 10% or higher.")
    fig_defects_pct = go.Figure(go.Indicator(
        mode="gauge+number", value=defects_pct_value,
        title={'text': "Total Defects % - Target < 5 %", 'font': {'size': 12}},
    gauge={'axis': {'range': [0, 100]},
        'bar': {'color': color},
        'steps': [{'range': [0, 50], 'color': "gray"},
                    {'range': [50, 75], 'color': "darkgray"},
                    {'range': [75, 100], 'color': "lightgray"}],
        'threshold': {'line': {'color': "#005DAA", 'width': 4},
                        'thickness': 0.75, 'value': 5 }}))
    fig_defects_pct.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_defects_pct, use_container_width=True)

# Add a negative margin to the divider below to remove extra space
st.markdown(
    """
    <style>
    .st-emotion-cache-13k62yr { margin-top: -2rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Visualization Tiles ---
st.markdown("---")
st.markdown("### Automation Overview")

v1, v0, v2 = st.columns([2,1,1 ])
with v1:
    automation_df = df[df['Call Category'].str.contains('Automation', na=False)]
    st.metric("Total Automation Calls", len(automation_df))
    dwayne_YTD_avg_hold()
    dwayne_YTD_top_avg_hold()
    #fig_category = chart_calls_by_category(df)
    #st.plotly_chart(fig_category, use_container_width=True)
    #sql_YTD_avg_hold()
    st.divider()
with v0:
    fig_donut_hold = donut_hold_time_breakdown(df, "Hold Time Breakdown")
with v2:

    support_table = support_lvl_table()

    defects_tbl = defects_table()
    auto_call_hold_time_by_shift()
v3, v4 = st.columns(2)
with v3:
    
    s1, s2 = st.columns(2)
    with s1:
        top_3_hold_times(df)
    with s2:
        pass



# --- Consolidate Data for PDF ---
kpi_data = {
    "Total Unique Calls": total_calls,
    "Avg Hold Time (min)": f"{avg_hold_time_min:.2f}",
    "% Answered < 5min": f"{answered_pct:.2f}%",
    "Avg Time to Resolution (min)": f"{auto_mttr_min:.2f}",
    "% Resolved by 3rd Lvl": f"{pct_resolved_3rd:.2f}%",
    "% Resolved < 7 Days": f"{pct_resolved_7_days:.2f}%",
    "Defects %": f"{defects_pct_value:.2f}%",
}

# Gather all figures for the PDF


# Generate PDF bytes (ensure your generate_performance_pdf can handle this dict structure)
pdf_bytes = "hello"
   # kpi_data=kpi_data,
   # charts=figs_for_pdf,
    #start_date=start_date.strftime('%b %d, %Y'),
    #end_date=end_date.strftime('%b %d, %Y')



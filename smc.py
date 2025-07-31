#smc.py
import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import numpy as np
import datetime

UPS_COLORS = [
    "#fbbb06", "#1d65b3", "#5c5c5c", "#94c4ec", "#340404", "#A56f15",
]

#Functions that will display data from Service Management Center (SMC)

'''
Data used:
total_auto_resolved: Total Automation Cases Resolved in past week
auto_3_resolved: 3rd lvl resolutions in past wk
auto_4_resolved: 4th lvl resolutions in past wk
auto_5_resolved: 5th level resolutions in past wk
auto_open_and_resolved: Cases opened and resolved within 7 days
total_defects: Total Defects
total_2_defects: 2nd Level Defects
total_tsg_defects: TSG defects
avg_auto_resolution_time: Average time for Automation resolution in week
east_resolved: Automation Cases Resolved east
west_resolved: Automation Cases Resolved west
inc_categorized: data on issues resolved last week (find top 4)
HELP: (non-emergency f/CC/Auto/District lvl)

'''
"""Metrics using this information:
** = used in external report
1. Number: % Resolved by 3rd Level Support**
    - auto_3_resolved/total_auto_resolved
2. Table to breakdown resolution level w count and %**
    - total_auto_resolved
    - auto_3_resolved
    - auto_4_resolved
    - auto_5_resolved
3. Number: % Cases resolved <7 Days**
    - auto_open_and_resolved
4. Table Defects broken down and %**
    - total_defects
    - total_2_defects
    - total_tsg_defects
5. Number: Time to resolution (Hrs)**
    - avg_auto_resolution_time
6. bar graph: total cases resolved east/west**
    - east_resolved
    - west_resolved
7. pie chart: most frequent issues
8. List: top 4 most frequent issues**
    - inc_categorized
"""

#Functions in Usage

"""This function will display the key information
top row: 1, 3, 5
in column 1: 1, 2, 4
in column 2: 3, 6
in column 3: 5, 8, (7?)
"""
def initialize_smc_poa():
    st.session_state.actual_mttr = 0.69
    st.session_state.actual_staff_for_week = 70
    st.session_state.actual_auto_defects = 3
    # Calculate percent of longest hold time in 0-5 min range using actual data if available
    hold_times = st.session_state.get("hold_times", np.random.uniform(0, 10, size=100))
    percent_0_5 = np.mean((hold_times >= 0) & (hold_times <= 5)) * 100
    st.session_state["percent_longest_hold_0_5"] = percent_0_5
def pct_resolved_3rd_lvl():
    
    total = (st.session_state.smc_total_auto_3resolved +
                st.session_state.smc_total_auto_4resolved +
                st.session_state.smc_total_auto_5resolved)
    return st.session_state.smc_total_auto_3resolved/ total *100
    pass
def pct_resolved_in_7_days():
    #this is a metric
    return st.session_state.smc_total_auto_open_resolved / st.session_state.smc_total_auto_resolved * 100
    pass
    
def avg_time_to_resolution():
    if "actual_mttr" not in st.session_state:
        st.session_state.actual_mttr = 0.67
    actual_mttr = st.session_state.actual_mttr
    st.metric("Time to Resolution (Hrs)", actual_mttr , help = "Average for past 7 Days")
    pass

def support_lvl_table():
    st.subheader("Level Support", help = "3 = BaSE Operators, 4 = BaSE Management, 5 = Vendor")
    # Table to breakdown resolution level w count and %
    levels = [3, 4, 5]
    counts = (
        st.session_state.smc_total_auto_3resolved,
        st.session_state.smc_total_auto_4resolved,
        st.session_state.smc_total_auto_5resolved,
    )
    total = sum(counts)
    percents = [f"{(c/total)*100:.1f}%" if total > 0 else "0.0%" for c in counts]
    df = pd.DataFrame({
        "Level": levels,
        "Count": counts,
        "Percent": percents
    })

    styled_df = df.style.set_properties(**{'text-align': 'center'}).set_table_styles(
        [{'selector': 'th', 'props': [('text-align', 'center')]}]
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

    
def region_bar():
    #bar graph showing count of east and west region resolutions
    data = pd.DataFrame({
        "Region": ["East", "West", "National"],
        "Cases Resolved": [st.session_state.smc_east_cases, st.session_state.smc_west_cases, st.session_state.smc_natl_cases]
    })
    fig = px.bar(
        data,
        x="Region",
        y="Cases Resolved",
        color="Region",
        color_discrete_sequence=UPS_COLORS[:2],
        title="Cases Resolved by Region"
    )
    fig.update_layout(showlegend=False, xaxis_title="Region", yaxis_title="Number of Cases Resolved")
    st.plotly_chart(fig, use_container_width=True)
    pass

def top_4_inc():
    # List: top 4 most frequent issues**
    st.write("**Top 4 Frequent Issues:**")
    for key, value in st.session_state.smc_frequent_issues.items():
        st.write(f"{key}: {value}")

def metric_total_defects():
    pass

def defects_table():

    #Table Defects broken down and %**
    st.subheader("**Defects**", help = "BaSE = 2nd Level, TSG = Technical Support Group, P5 = Low Priority")
    # Table Defects broken down and %
    defect_types = ["Base", "TSG", "P5"]
    counts = st.session_state.smc_lvl_2nd_defects, st.session_state.smc_TSG_defects, 10
    total = sum(counts)
    percents = [f"{(c/total)*100:.1f}%" for c in counts]
    df = pd.DataFrame({
        "Defects": defect_types,
        "Count": counts,
        "Percent": percents
    })
    styled_df = df.style.set_properties(**{'text-align': 'center'}).set_table_styles(
        [{'selector': 'th', 'props': [('text-align', 'center')]}]
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )
    st.session_state.actual_auto_defects = percents[0]  #set a session state variable for auto defects
    pass

def cases_breakdown_pie():
    #pie chart: most frequent issues
    st.image("images/smc_pie_cases.png")
    pass 
def total_defects_pct():
    dec = (st.session_state.smc_lvl_2nd_defects + st.session_state.smc_TSG_defects) / st.session_state.smc_total_auto_resolved
    return dec * 100
def smc_stats():
    st.header("Incident Metrics")
    c1, c2, c3 = st.columns(3)
    with c1:
        pct_resolved_3rd_lvl()
        st.divider()
        support_lvl_table()
        defects_table()
    with c2:
        pct_resolved_in_7_days()
        st.divider()
        region_bar()
    with c3:
        avg_time_to_resolution()
        st.divider()
        top_4_inc()
        cases_breakdown_pie()
    st.subheader("Preview SMC Data")
    st.markdown(
        '[Open SMC Dashboard in new tab](https://upsprod.service-now.com/now/nav/ui/classic/params/target/%24pa_dashboard.do%3Fsysparm_dashboard%3Df2fb07e12b4eae5058f9f88dbe91bfe1%26sysparm_tab%3D891cc7252b4eae5058f9f88dbe91bfc6%26sysparm_cancelable%3Dtrue%26sysparm_editable%3Dtrue%26sysparm_active_panel%3DaddWidgetSideContent)',
        unsafe_allow_html=True
    )
def smc_metrics():
    c1, c2, c3 = st.columns(3)
    with c1:
        pct_resolved_3rd_lvl()
    with c2:
        pct_resolved_in_7_days()
    with c3:
        avg_time_to_resolution()
    pass
def smc_form():
    st.subheader("2. Input SMC Data", help = "Service Management Center data inputs.")
    with st.form(key = "SMC"):
        
        st.markdown(
            '[Open SMC Dashboard in new tab](https://upsprod.service-now.com/now/nav/ui/classic/params/target/%24pa_dashboard.do%3Fsysparm_dashboard%3Df2fb07e12b4eae5058f9f88dbe91bfe1%26sysparm_tab%3D891cc7252b4eae5058f9f88dbe91bfc6%26sysparm_cancelable%3Dtrue%26sysparm_editable%3Dtrue%26sysparm_active_panel%3DaddWidgetSideContent)',
            unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            total_auto_resolved = st.number_input("Automation Cases Resolved (Last Week)", help= "1st of 5 on the left", min_value=0, max_value=1000, value=150, key='total_resolved')
            total_auto_3resolved = st.number_input("Cases Resolved 3rd Level (Last Week)", help= "3rd of 5 on the left", min_value=0, max_value=1000, value=70, key='total_3resolved')
            total_auto_4resolved = st.number_input("Cases Resolved 4th Level (Last Week)", help= "4th of 5 on the left", min_value=0, max_value=1000, value=70, key='total_4resolved')
            total_auto_5resolved = st.number_input("Cases Resolved 5th Level (Last Week)", help= "5th of 5 on the left", min_value=0, max_value=1000, value=70, key='total_5resolved')
            total_auto_open_resolved = st.number_input("Automation Cases Opened and Resolved (In Same Week)", help= "2nd of 5 on the left", min_value=0, max_value=1000, value=70, key='total_open_resolved')
        
        
        with col2:
            natl_cases = st.number_input("Automation P5's", help= "Automation P5 Defects", min_value=0, max_value=1000, value=70, key='natl')
            lvl_2nd_defects = st.number_input("2nd Level Defects", help= "Defects found in 2nd level support", min_value=0, max_value=100, value=10, key='2nd_lvl_defects')
            TSG_defects = st.number_input("TSG Defects", help= "Defects found in TSG support", min_value=0, max_value=100, value=10, key='TSG_defects')
            east_cases = st.number_input("East Cases Resolved", help= "Automation Cases Resolved by Region", min_value=0, max_value=1000, value=70, key='east')
            west_cases = st.number_input("West Cases Resolved", help= "Automation Cases Resolved by Region", min_value=0, max_value=1000, value=70, key='west')
        with col3:
            auto_mttr = st.number_input("Automation MTTR (min)", help= "Automation Cases Average Time to Resolution (Weekly)", min_value=0, max_value=1000, value=2, key='auto_mttr')
            freq_issue_1 = st.text_input("Frequent Issues (Top 1)", help= "Most Common Issue Resolved", value="Issue 1", key='freq_issue_1')
            freq_issue_2 = st.text_input("Frequent Issues (Top 2)", help= "Second Most Common Issue Resolved", value="Issue 2", key='freq_issue_2')
            freq_issue_3 = st.text_input("Frequent Issues (Top 3)", help= "Third Most Common Issue Resolved", value="Issue 3", key='freq_issue_3')
            freq_issue_4 = st.text_input("Frequent Issues (Top 4)", help= "Fourth Most Common Issue Resolved", value="Issue 4", key='freq_issue_4')
        #submit_smc = st.form_submit_button("Submit SMC Data")
    
            if st.form_submit_button('Save SMC Data'): 
                st.session_state.smc_total_auto_resolved = total_auto_resolved
                st.session_state.smc_total_auto_open_resolved = total_auto_open_resolved
                st.session_state.smc_total_auto_3resolved = total_auto_3resolved
                st.session_state.smc_total_auto_4resolved = total_auto_4resolved
                st.session_state.smc_total_auto_5resolved = total_auto_5resolved
                st.session_state.smc_auto_mttr = auto_mttr
                st.session_state.smc_east_cases = east_cases
                st.session_state.smc_west_cases = west_cases
                st.session_state.smc_natl_cases = natl_cases
                st.session_state.smc_lvl_2nd_defects = lvl_2nd_defects
                st.session_state.smc_TSG_defects = TSG_defects
                st.session_state.smc_frequent_issues = {
                    "Top 1": freq_issue_1,
                    "Top 2": freq_issue_2,
                    "Top 3": freq_issue_3,
                    "Top 4": freq_issue_4
                }
                st.success("SMC Data saved!")
        if total_auto_3resolved + total_auto_4resolved + total_auto_5resolved > total_auto_resolved:
            st.warning("Total Resolved is less than the sum of 3rd, 4th, and 5th level resolutions. Please check your inputs.")
        if total_auto_3resolved + total_auto_4resolved + total_auto_5resolved < total_auto_resolved:
            st.warning("Total Resolved is greater than the sum of 3rd, 4th, and 5th level resolutions. Please check your inputs.")
def smc():

    if 'smc_total_auto_resolved' in st.session_state:
        st.subheader("SMC Data Summary")
        x1, x2, x3 = st.columns(3)
        with x1:
            st.metric("Total Defects (%)", round(total_defects_pct(), 2))
        with x2:
            st.metric("Resolved by 3rd Level (%)", round(pct_resolved_3rd_lvl(), 2))
        with x3:
            st.metric("Cases Resolved < 7 Days (%)", round(pct_resolved_in_7_days(), 2))
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write(f"Total Automation Cases Resolved: {st.session_state.smc_total_auto_resolved}")
            st.write(f"Total Automation Cases Opened and Resolved: {st.session_state.smc_total_auto_open_resolved}")
            st.write(f"3rd Level Resolutions: {st.session_state.smc_total_auto_3resolved}")
            st.write(f"4th Level Resolutions: {st.session_state.smc_total_auto_4resolved}")
            st.write(f"5th Level Resolutions: {st.session_state.smc_total_auto_5resolved}")
        with c2:
            st.write(f"Average MTTR (min): {st.session_state.smc_auto_mttr}")
            st.write(f"East Cases Resolved: {st.session_state.smc_east_cases}")
            st.write(f"West Cases Resolved: {st.session_state.smc_west_cases}")
            st.write(f"National Cases Resolved: {st.session_state.smc_natl_cases}")
        with c3:
            st.write(f"2nd Level Defects: {st.session_state.smc_lvl_2nd_defects}")
            st.write(f"TSG Defects: {st.session_state.smc_TSG_defects}")
            st.write("Frequent Issues:")
            for key, value in st.session_state.smc_frequent_issues.items():
                st.write(f"- {key}: {value}")
    else:
        st.warning("No SMC data found. Please complete step 2.")

def sql_YTD_avg_hold():
    # Connect to SQL database (update connection string as needed)
    conn = pyodbc.connect(
        "DRIVER={SQL Server};SERVER=YOUR_SERVER;DATABASE=YOUR_DATABASE;Trusted_Connection=yes;"
    )
    query = """
        SELECT 
            [Hold Time(s)], 
            [Start Time]
        FROM [digium dashboard 2025]
        WHERE [Start Time] >= '2025-01-01 21:00:00'
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # Ensure datetime
    df['Start Time'] = pd.to_datetime(df['Start Time'])

    # Set week ending (Saturday) for each row
    df['week_ending'] = df['Start Time'] + pd.offsets.Week(weekday=5)
    df['week_ending'] = df['week_ending'].dt.normalize()

    # Group by week ending and calculate average hold time
    weekly_avg = (
        df.groupby('week_ending')['Hold Time(s)']
        .mean()
        .reset_index()
        .rename(columns={'Hold Time(s)': 'avg_hold_time_s'})
    )

    # Only include weeks up to today
    today = pd.Timestamp.today().normalize()
    weekly_avg = weekly_avg[weekly_avg['week_ending'] <= today]

    # Plot
    fig = px.line(
        weekly_avg,
        x='week_ending',
        y='avg_hold_time_s',
        title='Weekly Average Hold Time (s)',
        markers=True
    )
    fig.update_layout(xaxis_title='Week Ending', yaxis_title='Average Hold Time (s)')
    st.plotly_chart(fig, use_container_width=True)

    return weekly_avg
    
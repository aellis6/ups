# pages/3_Custom_Report_Builder.py
import streamlit as st
import pandas as pd
from utils import create_global_sidebar, display_active_filters # NEW
# --- Page Setup ---
st.set_page_config( 
    page_title="Custom Dashboard", 
    layout="wide", 
    page_icon="images/upslogo.png" 
) 
st.title("Custom Report Builder")
st.markdown("Select dimensions and metrics to build your own summary table from the filtered data.")
create_global_sidebar()
# --- Data Loading and Validation ---
if 'df_filtered' not in st.session_state or st.session_state['df_filtered'] is None:
    st.warning("Please upload and filter data to build a report.")
    st.stop()
df = st.session_state['df_filtered'].copy()
if df.empty:
    st.warning("No data loaded yet. Please upload a file on the Home page.")
    st.stop()
# Display the active filters for context
display_active_filters()
st.divider()
# --- Report Builder UI ---
c1, c2, c3 = st.columns(3)
with c1:
    # Let the user choose how to group the data
    dimensions_all = df.select_dtypes(include='object').columns.tolist()
    # Add key categorical columns that might not be 'object' type
    dimensions_all.extend(['DayOfWeek', 'Hour', 'Queue ID', 'Shift', 'AgentName'])
    selected_dims = st.multiselect(
        "Group By (Dimensions):",
        options=sorted(list(set(dimensions_all))),
        default=['Call Category']
    )
with c2:
    # Let the user choose what to measure
    metrics_all = df.select_dtypes(include='number').columns.tolist()
    selected_metrics = st.multiselect(
        "Calculate (Metrics):",
        options=sorted(metrics_all),
        default=['Hold Time (s)']
    )
with c3:
    # Let the user choose how to calculate
    agg_func = st.selectbox(
        "Using function:",
        options=["sum", "mean", "count", "max", "min"],
        index=1 # Default to mean (average)
    )
# --- Generate and Display Report ---
st.divider()
if not selected_dims or not selected_metrics:
    st.info("Please select at least one Dimension and one Metric to generate a report.")
elif df.empty:
    st.info("No data available for the current filter selections to build a report.")
else:
    try:
        # Create the aggregation dictionary
        agg_dict = {metric: agg_func for metric in selected_metrics}
        # Always include a count of the calls in the group
        agg_dict['Call ID'] = 'count'
        # The powerful groupby and aggregation function
        report_df = df.groupby(selected_dims, as_index=False).agg(agg_dict)
        report_df.rename(columns={'Call ID': 'Number of Calls'}, inplace=True)
        st.subheader("Your Custom Report")
        st.dataframe(report_df)
        csv = report_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Report as CSV", csv, "custom_report.csv", "text/csv")
    except Exception as e:
        st.error(f"Could not generate report. Please check your selections. Error: {e}")


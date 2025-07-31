# utils.py
import streamlit as st
import pandas as pd
import plotly.express as px
#from weasyprint import HTML
import base64
import numpy as np
import tempfile
from smc import smc_metrics
import decimal



# --- 1. Constants, Colors, and Default Mappings ---
# columns that MUST exist in the uploaded Digium CSV
REQUIRED_COLUMNS = {
    "Call ID", "Start Time", "From", "To", "Total Duration", "Talk Duration",
    "Who Hung Up", "Abandoned", "Hold Time (s)", "Queue ID", "Extension"
}
# The official UPS color palette for consistent branding in charts
UPS_COLORS = [
    "#351c15",  # UPS Brown
    "#fbbb06",  # UPS Yellow
    "#006699",  # UPS Blue
    "#94c4ec",  # Light Blue
    "#340404",  # Dark Brown
    "#A56f15",  # Gold/Bronze
]
# The default agent map, used if a custom mapping file is not provided.
DEFAULT_AGENT_MAP = {
    100: "Agonna Powell", 104: "Gabriel Herrera", 106: "CBRE Prioritized",
    107: "Christopher Treadaway", 108: "Aziza Salmon", 109: "Ian Raudes-Palacio",
    110: "Nick Kipreos", 111: "Badr Goubi", 112: "Scott Rhodig",
    113: "Christopher Knotts", 114: "Mark Rorer", 115: "James Chestnut",
    116: "David Hernandez", 118: "Nick Biester", 119: "Isaiah Devoe",
    121: "La Shawn George", 122: "Ropekia Gunn", 124: "Spare 124",
    125: "Michael Henderson", 127: "Spare 127", 129: "Santo Nesbitt",
    130: "Fire Transfer", 133: "Tyler Townsend", 135: "Darious Massey",
    141: "Saindon Balunis", 142: "Jey Zamora", 145: "Logan Flowers",
    146: "Ongela Helm", 162: "Frankie Robinson", 163: "Kailee Sesler",
    164: "Melissa Lopez", 165: "Ali Eljayar", 166: "Terri Angerbauer",
    302: "Yulia Bachman", 304: "SFR4CBRE Extension", 306: "Charles Giles",
    308: "Jarrod Roberts", 311: "Babrah Koroma", 312: "Michael Roberts",
    313: "Antony Wanja", 314: "Todd Mims", 315: "CBRE Transfer Numbers View",
    316: "CBRE Transfer", 520: "Kathleen Caste", 540: "Jae Lim",
    555: "CBRE Phase In", 560: "Henry Blankson", 580: "Chris Otto",
    620: "Travis Webbe", 806: "ConventionalConveyor", 807: "xNew Main Test",
    854: "Manager Critical", 888: "SFR Primary", 899: "Voicemail Access",
    901: "Automation", 902: "Facility Issues", 903: "CBRE Returned Calls",
    904: "CBRE Transfer Queue", 905: "Fire Transfer", 910: "GTSG Leadership",
    999: "BaSE Main"
}
# --- 2. Data Loading and Processing Functions ---
def get_name_from_extension(extension_id):
    try:
        # Prioritize custom map from session state, fall back to default
        agent_map = st.session_state.get('agent_map_custom') or DEFAULT_AGENT_MAP
        return agent_map.get(str(extension_id), f"Unknown Ext {extension_id}")
    except (ValueError, TypeError):
        return str(extension_id) # Return as string if not a valid integer
@st.cache_data
def process_uploaded_file(uploaded_file):
    """Loads, validates, cleans, and engineers features from the uploaded call data."""
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Error reading the CSV file: {e}")
        return None
    if not REQUIRED_COLUMNS.issubset(df.columns):
        missing = REQUIRED_COLUMNS - set(df.columns)
        st.error(f"File Structure Mismatch! Missing required columns: {', '.join(missing)}")
        return None
    df["Start Time"] = pd.to_datetime(df["Start Time"], errors="coerce")
    df = df.dropna(subset=["Start Time"])
    df["Queue ID"] = df["Queue ID"].astype(str).str.strip()
    df["Extension"] = df["Extension"].astype(str).str.strip()
    df["Abandoned_Flag"] = df["Abandoned"].astype(str).str.strip().str.lower() == "true"
    for col in ["Total Duration", "Talk Duration", "Hold Time (s)"]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df["Hour"] = df["Start Time"].dt.hour
    df["DayOfWeek"] = df["Start Time"].dt.day_name()
    def get_shift(row):
        """Categorizes a call into a shift based on its exact start time."""
        call_time = row['Start Time'].time()
        preload_start = pd.to_datetime('04:30:00').time()
        twilight_start = pd.to_datetime('12:30:00').time()
        night_start = pd.to_datetime('20:30:00').time()
        if preload_start <= call_time < twilight_start:
            return "Preload (4:30am - 12:29pm)"
        elif twilight_start <= call_time < night_start:
            return "Twilight (12:30pm - 8:29pm)"
        else:
            return "Night (8:30pm - 4:29am)"
    df['Shift'] = df.apply(get_shift, axis=1)
    def assign_call_category(row):
        #logic for returned automation is if "return" in str(row["From"]).lower() and queue_id == "999"
        queue_id = str(row["Queue ID"])
        if queue_id == "304": return "CBRE SFR"
        elif queue_id == "316": return "CBRE Legacy"
        elif queue_id == "901":
            return "Returned Automation" if "return" in str(row["From"]).lower() and queue_id == "999" else "Automation"
        elif queue_id in ["854", "910"]: return "Managers"
        else: return "Other"
    df["Call Category"] = df.apply(assign_call_category, axis=1)
    # Add agent name directly during processing
    df['AgentName'] = df['Extension'].apply(get_name_from_extension)
    return df
@st.cache_data
def load_agent_mapping_from_file(uploaded_file):
    """Reads an agent mapping XLSX and returns a dictionary."""
    if uploaded_file is None:
        return None
    try:
        # Read the XLSX file
        map_df = pd.read_excel(uploaded_file)
        map_df.columns = ['Extension', 'AgentName']
        map_df['Extension'] = pd.to_numeric(map_df['Extension'], errors='coerce')
        map_df = map_df.dropna(subset=['Extension'])
        map_df['Extension'] = map_df['Extension'].astype(int)
        # Directly convert to dictionary without writing/reading temp file
        return pd.Series(map_df['AgentName'].values, index=map_df['Extension']).to_dict()
    except Exception as e:
        st.error(f"Error reading agent mapping file: {e}")
        return None
# --- 3. Global Sidebar Function ---
def reset_filters(df):  
    """Resets all filters to their default state."""
    st.session_state['df_filtered'] = df.copy()  # Reset to original data
    st.session_state['filter_selections'] = {
        "Date Range": (df["Start Time"].min().strftime('%Y-%m-%d'), df["Start Time"].max().strftime('%Y-%m-%d')),
        "Days": ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        "Shifts": sorted(df["Shift"].unique()),
        "Categories": ['Automation', 'Returned Automation'],
        "Agents": sorted(df["AgentName"].unique())
    }
def create_global_sidebar():
    """Creates the sidebar filters that appear on all pages."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background-color: #340404 !important;
            color: black !important;
        }
        [data-testid="stSidebar"] * {
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Only show filters if data has been uploaded and processed
    if 'df_original' not in st.session_state or st.session_state['df_original'] is None or st.session_state['df_original'].empty:
        st.sidebar.warning("Upload Digium call data on the Home page to activate filters.")
        st.session_state['df_filtered'] = pd.DataFrame()  # Ensure filtered df exists
        return

    st.sidebar.header("Global Filter Options")
    df = st.session_state['df_original']
    st.sidebar.button("Reset Filters", on_click=lambda: reset_filters(df))
    st.sidebar.button("Apply New")
    # --- Collect all filter values from widgets ---
    start_date, end_date = st.sidebar.date_input(
        "Date Range",
        value=(df["Start Time"].min().date(), df["Start Time"].max().date())
    )
    days_opts = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Weekends Only']
    selected_days = st.sidebar.multiselect(
        "Day(s) of Week",
        options=days_opts,
        default=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    )
    selected_shifts = st.sidebar.multiselect(
        "Filter by Shift",
        options=sorted(df["Shift"].unique()),
        default=sorted(df["Shift"].unique())
    )
    # Add Returned Automation as a separate filter section
    st.sidebar.markdown("### Returned Automation Calls")
    returned_auto_options = ["Include Returned Automation Calls"]
    include_returned_auto = st.sidebar.checkbox(
        "Include Returned Automation Calls",
        value=True
    )

    # Category filter
    category_options = sorted(df["Call Category"].unique())
    # Always include 'Returned Automation' in default if present
    default_categories = [cat for cat in ['Automation', 'Returned Automation'] if cat in category_options]
    if include_returned_auto and 'Returned Automation' not in default_categories and 'Returned Automation' in category_options:
        default_categories.append('Returned Automation')
    elif not include_returned_auto and 'Returned Automation' in default_categories:
        default_categories.remove('Returned Automation')
    selected_categories = st.sidebar.multiselect(
        "Call Category",
        options=category_options,
        default=default_categories if default_categories else category_options
    )
    # Filter by Agent
    with st.sidebar.expander("Filter by Agent"):
        all_agents = sorted(df["AgentName"].unique())
        selected_agents = st.multiselect("Filter by Agent", options=all_agents, default=all_agents)

    # --- Efficiently apply all filters at once ---
    day_mask = df["DayOfWeek"].isin(['Saturday', 'Sunday']) if "Weekends Only" in selected_days else df["DayOfWeek"].isin(selected_days)
    final_mask = (
        (df["Start Time"].dt.date >= start_date) & (df["Start Time"].dt.date <= end_date) &
        (day_mask) &
        (df["Shift"].isin(selected_shifts)) &
        (df["Call Category"].isin(selected_categories)) &
        (df["AgentName"].isin(selected_agents))
    )
    # Save the filtered dataframe for pages to use
    st.session_state['df_filtered'] = df[final_mask]
    st.session_state['filter_selections'] = {
        "Date Range": (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
        "Days": selected_days,
        "Shifts": selected_shifts,
        "Categories": selected_categories,
        "Agents": selected_agents
    }






# --- 4. Metric Calculation Functions  ---
#function that identifies calls that have more than 2 queues traversed excluding 999
#for dataframe look at columns "Traversed"
#if 

def auto_call_hold_time_by_shift():
    df = st.session_state.get("df_filtered")
    if df is None or df.empty:
        return pd.DataFrame(columns=["Shift", "Average Hold Time (min)"])
    df["Hold Time (min)"] = df["Hold Time (s)"] / 60
    df = df.groupby("Shift")["Hold Time (min)"].mean().reset_index()
    df = df.rename(columns={"Hold Time (min)": "Average Hold Time (min)"})
    if df.empty:
        st.write("No data available for Hold Times by Shift.")
        return
    st.write("### Hold Times by Shift")
    # Hide the index (row numbers) in the dataframe display
    st.dataframe(
        df.style.set_properties(**{'text-align': 'right-align'}),
        use_container_width=True,
        hide_index=True
    )

def metric_total_calls(df):
    """Calculates total calls this week vs last week."""
    if df.empty:
        st.metric("Total Calls (This Week)", value=0, delta="0")
        return
    latest_date = df["Start Time"].max()
    this_week_start = latest_date - pd.Timedelta(days=6)
    last_week_start = this_week_start - pd.Timedelta(days=7)
    last_week_end = this_week_start - pd.Timedelta(days=1)
    this_total = df[(df["Start Time"] >= this_week_start) & (df["Start Time"] <= latest_date)].shape[0]
    last_total = df[(df["Start Time"] >= last_week_start) & (df["Start Time"] <= last_week_end)].shape[0]
    delta = this_total - last_total if last_total > 0 else None
    st.metric("Total Calls (This Week)", value=this_total, delta=delta)
def top_3_hold_times(df):
    st.write("**Top 3 Longest Hold Times (min)**")
    if df.empty or "Hold Time (s)" not in df.columns:
        st.write("No data.")
        return
    top = df.nlargest(3, "Hold Time (s)")[["AgentName", "Hold Time (s)"]]
    for _, row in top.iterrows():
        st.write(f"{row['Hold Time (s)']/60:.2f} min ({row['AgentName']})")
def top_3_talk_times(df):
    st.write("**Top 3 Talk Times (min)**")
    if df.empty or "Talk Time (s)" not in df.columns:
        st.write("No data.")
        return
    top = df.nlargest(3, "Talk Time (s)")[["AgentName", "Talk Time (s)"]]
    for _, row in top.iterrows():
        st.write(f"{row['Talk Time (s)']/60:.2f} min ({row['AgentName']})")
# --- 5. Charting Functions  ---
def chart_calls_by_category(df):
    """Creates a pie chart of calls by category."""
    if df.empty: return None
    counts = df['Call Category'].value_counts().reset_index()
    fig = px.pie(counts, names='Call Category', values='count', title='Calls by Category',
                 hole=0.4, color_discrete_sequence=UPS_COLORS)
    return fig
def donut_hold_time_breakdown(df, title):
    """Creates a donut chart of hold time ranges and displays a breakdown table."""
    if df.empty:
        return None
    df["Hold Time (min)"] = pd.to_numeric(df["Hold Time (s)"], errors="coerce") / 60
    bins = [0, 5, 10, 15, 30, float("inf")]
    labels = ["0–5 min", "5–10 min", "10–15 min", "15–30 min", "30+ min"]
    df["Hold Range"] = pd.cut(df["Hold Time (min)"], bins=bins, labels=labels, right=False)
    breakdown = df["Hold Range"].value_counts(normalize=False, sort=False).reset_index()
    breakdown.columns = ["Hold Time Range", "Count"]
    total = breakdown["Count"].sum()
    breakdown["Percent"] = (breakdown["Count"] / total * 100).round(2)
    fig = px.pie(
        breakdown,
        names="Hold Time Range",
        values="Count",
        hole=0.4,
        title=title,
        color_discrete_sequence=UPS_COLORS
    )
    #st.plotly_chart(fig, use_container_width=True, key="hold")
    # Hide the index (left column with 0 1 2 3 4)
    st.dataframe(breakdown, use_container_width=True, hide_index=True, key="hold1")
    #return fig
# --- 6. Layout, PDF, and UI Helper Functions ---
def display_active_filters():
    df_preview = st.session_state.get("df_filtered") 

    """Displays a summary of the currently applied global filters."""
    if 'filter_selections' in st.session_state and st.session_state['df_original'] is not None:
        selections = st.session_state['filter_selections']
        st.subheader("Active Call Filters Summary")
        date_str = f"**Date Range:** {selections['Date Range'][0]} to {selections['Date Range'][1]}"
        days_str = f"**Days:** {', '.join(selections['Days'])}"
        shifts_str = f"**Shifts:** {', '.join(selections['Shifts'])}"
        cat_str = f"**Categories:** {', '.join(selections['Categories'])}"
        # Check if all agents are selected for a cleaner display
        total_agents = len(st.session_state['df_original']['AgentName'].unique())
        agent_str = f"**Agents:** All" if len(selections['Agents']) == total_agents else f"**Agents:** {len(selections['Agents'])} selected"
        raw_rows = len(st.session_state['df_original'])
        filtered_rows = len(st.session_state['df_filtered']) if 'df_filtered' in st.session_state else 0
        rows_str = f"**Rows:** {filtered_rows} of {raw_rows} after filters applied"
        st.markdown(f"{date_str}  \n{days_str}  \n{shifts_str}  \n{cat_str}  \n{agent_str}  \n{rows_str}")
        with st.expander("Preview Table"):
            st.dataframe(df_preview)   
def load_digium_kpi(df):
    if df.empty:
        st.info("No data available for the selected filters.")
        return
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(
            label="Total Calls",
            value=len(df), #old was ['Call ID'].nunique(),
            help="Total Unique Call IDs"
        )
    with kpi2:
        avg_hold_time_min = pd.to_numeric(df['Hold Time (s)'], errors='coerce').mean() / 60
        st.metric("Average Hold Time (min)", f"{avg_hold_time_min:.2f}")
    with kpi3:
        answered_under_5min = pd.to_numeric(df['Hold Time (s)'], errors='coerce') < 300
        percent_answered = (answered_under_5min.sum() / len(df)) * 100 if len(df) > 0 else 0
        st.metric("% Answered < 5 min", f"{percent_answered:.2f}%")
    with kpi4:
        abandoned_mask = df['Abandoned'].astype(str).str.strip().str.lower() == "true"
        percent_abandoned = (abandoned_mask.sum() / len(df)) * 100 if len(df) > 0 else 0
        st.metric("% Abandoned", f"{percent_abandoned:.2f}%")

def hold_top3_shift(df):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Top Call Characteristics")
        fig_top_hold = top_3_hold_times(df)
        if fig_top_hold is not None:
            st.plotly_chart(fig_top_hold, use_container_width=True)
        else:
            st.write("No data available for Top 3 Longest Hold Times.")
    with c2:
        auto_call_hold_time_by_shift()

def _sanitize_key(s: str) -> str:
    # replace spaces and disallowed chars, keep it short
    key = s.lower().replace(" ", "_")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_"
    key = "".join(ch for ch in key if ch in allowed)
    return key[:30]  # cap length to avoid overly long keys

def donut_hold_time_breakdown(df, title, key_suffix: str | None = None):
    """Creates a donut chart of hold time ranges and displays a breakdown table."""
    if df.empty:
        st.write("No data available.")
        return None

    df["Hold Time (min)"] = pd.to_numeric(df["Hold Time (s)"], errors="coerce") / 60
    bins = [0, 5, 10, 15, 30, float("inf")]
    labels = ["0–5 min", "5–10 min", "10–15 min", "15–30 min", "30+ min"]
    df["Hold Range"] = pd.cut(
        df["Hold Time (min)"], bins=bins, labels=labels, right=False
    )
    breakdown = (
        df["Hold Range"]
        .value_counts(normalize=False, sort=False)
        .reset_index()
    )
    breakdown.columns = ["Hold Time Range", "Count"]
    total = breakdown["Count"].sum()
    breakdown["Percent"] = (breakdown["Count"] / total * 100).round(2)

    fig1 = px.pie(
        breakdown,
        names="Hold Time Range",
        values="Count",
        hole=0.4,
        title=title,
        color_discrete_sequence=UPS_COLORS,
    )

    base = title if key_suffix is None else f"{title}_{key_suffix}"
    safe_base = _sanitize_key(base)
    chart_key = f"hold_{safe_base}"
    table_key = f"hold_table_{safe_base}"

    st.plotly_chart(fig1, use_container_width=True, key=chart_key)
    st.dataframe(breakdown, use_container_width=True, key=table_key)

    return fig1

def top_3_hold_times(df):
    st.write("**Top 3 Hold Times (min)**")
    if df.empty or "Hold Time (s)" not in df.columns:
        st.write("No data.")
        return
    top = df.nlargest(3, "Hold Time (s)")[["AgentName", "Hold Time (s)"]]
    for _, row in top.iterrows():
        st.write(f"{row['Hold Time (s)']/60:.2f} min ({row['AgentName']})")
def top_3_talk_times(df):
    """Top 3 calls with the largest sum of hold time and talk time (in minutes)."""
    st.write("**Top 3 Call Times (min)**")
    if df.empty or "Talk Time (s)" not in df.columns or "Hold Time (s)" not in df.columns:
        st.write("No data.")
        return
    # Calculate total call time for each row
    df = df.copy()
    df["Total Call Time (s)"] = df["Hold Time (s)"] + df["Talk Time (s)"]
    top = df.nlargest(3, "Total Call Time (s)")[["AgentName", "Total Call Time (s)"]]
    for _, row in top.iterrows():
        st.write(f"{row['Total Call Time (s)']/60:.2f} min ({row['AgentName']})")
def dwayne_YTD_avg_hold():
    conn = st.connection('mysql', type='sql')
    if conn is None:
        st.error("Failed to connect to the SQL database.")
        return

    query = """
    SELECT
      DATE_ADD(`Start Time`, INTERVAL ((7 - DAYOFWEEK(`Start Time`)) % 7) DAY) AS week_end_date,
      AVG(`Hold Time (s)`) / 60.0 AS avg_hold_time_min
    FROM `digium dashboard 2025`
    WHERE `Hold Time (s)` IS NOT NULL
      AND `Start Time` IS NOT NULL
      AND `Start Time` >= CONCAT(YEAR(CURDATE()), '-01-01')
    GROUP BY week_end_date
    ORDER BY week_end_date
    """
    df = conn.query(query, ttl=600)
    if df is None or df.empty:
        st.warning("No data returned from the query.")
        return

    # Normalize types
    df['week_end_date'] = pd.to_datetime(df['week_end_date'], errors='coerce')
    df = df.sort_values('week_end_date')
    if df.empty:
        st.warning("No valid data after parsing dates.")
        return

    # Fill in missing Saturdays between first and last
    min_week = df['week_end_date'].min()
    max_week = df['week_end_date'].max()
    all_saturdays = pd.date_range(start=min_week, end=max_week, freq='W-SAT')
    weekly = (
        df.set_index('week_end_date')
          .reindex(all_saturdays)
          .rename_axis('week_end_date')
          .reset_index()
    )

    # Label for ticks
    weekly['WE_label'] = weekly['week_end_date'].dt.strftime('WE %m/%d')

    # Plot
    fig = px.line(
        weekly,
        x='week_end_date',
        y='avg_hold_time_min',
        title='YTD Avg Hold Time per Week (Sunday–Saturday)',
        labels={'avg_hold_time_min': 'Avg Hold Time in Minutes', 'week_end_date': 'Week Ending'},
        markers=True,
    )

    fig.update_traces(
        name='Avg Hold Time',
        text=weekly['avg_hold_time_min'].round(2),
        textposition='top center',
        line=dict(width=4, color='#351c15'),
    )

    # Trendline fit on non-NaN weeks
    valid = weekly['avg_hold_time_min'].notna()
    if valid.sum() > 1:
        trend_x = weekly.loc[valid, 'week_end_date'].map(pd.Timestamp.toordinal).to_numpy()
        trend_y = weekly.loc[valid, 'avg_hold_time_min'].to_numpy()
        coeffs = np.polyfit(trend_x, trend_y, 1)
        poly = np.poly1d(coeffs)
        all_x_ord = weekly['week_end_date'].map(pd.Timestamp.toordinal).to_numpy()
        trend_vals = poly(all_x_ord)
        fig.add_scatter(
            x=weekly['week_end_date'],
            y=trend_vals,
            mode='lines',
            line=dict(color='#fbbb06', width=2, dash='dot'),
            name='Trendline',
        )

    fig.update_layout(
        plot_bgcolor='#23272b',
        paper_bgcolor='#23272b',
        font=dict(color='white', size=16, family='Arial Black'),
        title_font=dict(size=24, color='white', family='Arial Black'),
        xaxis=dict(
            showgrid=False,
            tickangle=45,
            tickmode='array',
            tickvals=weekly['week_end_date'],
            ticktext=weekly['WE_label'],
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#444',
            zeroline=True,
            zerolinecolor='#888',
            rangemode='tozero',
        ),
        showlegend=True,
        legend=dict(font=dict(color='white')),
        margin=dict(t=70, b=120),
    )

    st.plotly_chart(fig, use_container_width=True)
def dwayne_YTD_top_avg_hold2(min_per_week=1):
    conn = st.connection('mysql', type='sql')
    if conn is None:
        st.error("Failed to connect to the SQL database.")
        return

    query = """
    SELECT call_id,
           call_start_time,
           hold_time_seconds,
           system_name
    FROM `call center metrics ytd 2025`
    WHERE system_name = 'MHE Automated Systems'
      AND hold_time_seconds IS NOT NULL
      AND call_start_time IS NOT NULL
      AND call_start_time >= CONCAT(YEAR(CURDATE()), '-01-01')
    """
    df = conn.query(query, ttl=600)
    if df is None or df.empty:
        st.warning("No data returned from the query.")
        return

    # Parse and normalize
    df['call_start_time'] = pd.to_datetime(df['call_start_time'], errors='coerce')
    df['week_end_date'] = df['call_start_time'].apply(
        lambda d: d - pd.Timedelta(days=(d.weekday() - 5) % 7) if pd.notnull(d) else pd.NaT
    )
    df['hold_time_seconds'] = pd.to_numeric(df['hold_time_seconds'], errors='coerce')
    df = df.dropna(subset=['week_end_date', 'hold_time_seconds'])

    # Top 3 per week
    df_sorted = df.sort_values(['week_end_date', 'hold_time_seconds'], ascending=[True, False])
    df_top3 = df_sorted.groupby('week_end_date').head(3)

    # Debug output: which top values were picked
    for week, group in df_top3.groupby('week_end_date'):
        values = group['hold_time_seconds'].tolist()
        minutes = [v / 60.0 for v in values]
        st.write(f"Week Ending {week.strftime('%Y-%m-%d')}: top hold times (s) {values} -> (min) {[round(m, 2) for m in minutes]}")

    # Average and convert to minutes
    avg_df = df_top3.groupby('week_end_date')['hold_time_seconds'].mean().reset_index()
    avg_df['value'] = avg_df['hold_time_seconds'] / 60.0
    avg_df = avg_df.sort_values('week_end_date')

    # Optionally enforce minimum number of samples per week
    counts = df_top3.groupby('week_end_date').size()
    if min_per_week > 1:
        valid_weeks = counts[counts >= min_per_week].index
        avg_df = avg_df[avg_df['week_end_date'].isin(valid_weeks)]

    if avg_df.empty:
        st.warning("No weekly averages computed after applying filters.")
        return

    # Label and trendline
    avg_df['WE'] = avg_df['week_end_date'].dt.strftime('WE %m/%d')
    x_numeric = avg_df['week_end_date'].map(pd.Timestamp.toordinal).to_numpy()
    y = avg_df['value'].to_numpy()
    if len(x_numeric) >= 2:
        m, b = np.polyfit(x_numeric, y, 1)
        trend_values = m * x_numeric + b
    else:
        trend_values = y.copy()
    avg_df['trend'] = trend_values

    # Plot
    fig = px.line(
        avg_df,
        x='WE',
        y='value',
        title='YTD Avg Top 3 Hold Times (minutes)',
        labels={'value': 'Hold Avg (min)', 'WE': 'Week Ending'},
        markers=True
    )
    fig.update_traces(
        selector=dict(mode='lines+markers'),
        text=avg_df['value'].round(2),
        textposition="top center",
        line=dict(width=5, color='#006699')
    )
    # add trendline
    fig.add_trace(px.line(avg_df, x='WE', y='trend').data[0])
    fig.data[-1].update(line=dict(color='orange', dash='dash'), name='Trendline')

    fig.update_layout(
        plot_bgcolor='#23272b',
        paper_bgcolor='#23272b',
        font=dict(color='white', size=16, family='Arial Black'),
        title_font=dict(size=28, color='white', family='Arial Black'),
        xaxis=dict(showgrid=False, tickangle=45),
        yaxis=dict(
            showgrid=True,
            gridcolor='#444',
            zeroline=True,
            zerolinecolor='#888',
            range=[0, max(avg_df['value'].max(), 120)]
        ),
        showlegend=False
    )

    #st.dataframe(avg_df[['week_end_date', 'WE', 'value', 'trend']], use_container_width=True)
    st.plotly_chart(fig, use_container_width=True)

def dwayne_YTD_top_avg_hold():
    #this should show average of the top 3 longest hold times for each week ending date.
    conn = st.connection('mysql', type='sql')
    if conn is None:
        st.error("Failed to connect to the SQL database.")
        return

    #st.image("images/YTD_avg_hold.png")

    query = """
    SELECT week_end_date, value 
    FROM `call center metrics ytd 2025`
    WHERE system_name = 'MHE Automated Systems' 
      AND metric_name = 'Top 3 Longest Hold Times (min.)'
    ORDER BY week_end_date, value DESC
    """
    df = conn.query(query, ttl=600)
    if df is None or df.empty:
        st.warning("No data returned from the query.")
        return

    df['week_end_date'] = pd.to_datetime(df['week_end_date'], errors='coerce')
    # Align to previous (or same) Saturday if not already
    df['week_end_date'] = df['week_end_date'].apply(
        lambda d: d - pd.Timedelta(days=(d.weekday() - 5) % 7) if pd.notnull(d) else d
    )

    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['week_end_date', 'value'])

    # Take top 3 values for each week_end_date, average them
    df_sorted = df.sort_values(['week_end_date', 'value'], ascending=[True, False])
    df_top3 = df_sorted.groupby('week_end_date').head(3)

    # DEBUG: Show top 3 values for each week
   # for week, group in df_top3.groupby('week_end_date'):
        #st.write(f"Week Ending {week.strftime('%Y-%m-%d')}: {group['value'].tolist()}")

    avg_df = df_top3.groupby('week_end_date')['value'].mean().reset_index()
    avg_df = avg_df.sort_values('week_end_date')

    # Format x-axis as "WE mm/dd"
    avg_df['WE'] = avg_df['week_end_date'].dt.strftime('WE %m/%d')

    #st.dataframe(avg_df, use_container_width=True)

    # Plot main line using formatted WE, but trendline using datetime
    fig = px.line(
        avg_df,
        x='WE',
        y='value',
        title='YTD Avg Top 3 Hold Times',
        labels={'value': 'Hold Avg', 'WE': 'Week Ending'},
        markers=True
    )
    fig.update_traces(text=avg_df['value'].round(2), textposition="top center", line=dict(width=5, color='#006699'))

    # Add trendline using week_end_date (datetime)
    fig_trend = px.scatter(
        avg_df,
        x='week_end_date',
        y='value',
        trendline='ols'
    )
    # Overlay only the trendline (orange, dashed)
    for trace in fig_trend.data:
        if trace.mode == 'lines':
            trace.line.color = 'orange'
            trace.line.dash = 'dash'
            # Re-map x to WE for display
            trace.x = avg_df['WE']
            fig.add_trace(trace)

    fig.update_layout(
        plot_bgcolor='#23272b',
        paper_bgcolor='#23272b',
        font=dict(color='white', size=16, family='Arial Black'),
        title_font=dict(size=28, color='white', family='Arial Black'),
        xaxis=dict(showgrid=False, tickangle=45),
        yaxis=dict(showgrid=True, gridcolor='#444', zeroline=True, zerolinecolor='#888', range=[0, max(avg_df['value'].max(), 120)]),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    #st.image("images/YTD_top_hold.png")
def auto_calls_line_graph(df):
    pass
    st.info("Total Automation Calls by WE YTD Line Graph")
    st.warning("Need SQL database for historical data")
    st.image("images/digium1.png")

def auto_avg_resolution_bar(df):
    pass
    st.info("(SMC) Automation Avg. Resolution Time by Week Ending line graph")
    st.warning("Need SQL and SMC link database for historical data")
    st.image("images/auto_smc1_bar.png")

def auto_percent_resolved(df):
    pass
    st.info("(SMC) % Automation Cases Resolved <7 Days bar chart")
    st.warning("Need SQL and SMC database for historical data")
    st.image("images/smc3.png")

def shifts(df):
    st.info("(Teams) Automation Support - Number of Shifts Week Ending Bar Chart")
    st.write(f"Actual Staff: {st.session_state.actual_staff_for_week}")
    st.warning("Need SQL database for historical data")
    st.image("images/teams1.png")

def poa_table(df):
    # Access POA values from session state
    poa_conventional_defects = st.session_state.get('poa_conventional_defects', 5.0)
    poa_tsg_defects = st.session_state.get('poa_tsg_defects', 5.0)
    poa_base_defects = st.session_state.get('poa_base_defects', 5.0)
    poa_facility_sfr = st.session_state.get('poa_facility_sfr', 90.0)
    poa_automation_wait = st.session_state.get('poa_automation_wait', 90.0)
    poa_conventional_mttr = st.session_state.get('poa_conventional_mttr', 2.0)
    poa_automation_mttr = st.session_state.get('poa_automation_mttr', 1.0)

    poa_data = {
        "Conventional Defects (%)": poa_conventional_defects,
        "TSG Defects (%)": poa_tsg_defects,
        "BaSE Defects (%)": poa_base_defects,
        "Facility SFR Wait (%)": poa_facility_sfr,
        "Automation Wait (%)": poa_automation_wait,
        "Conventional MTTR (hrs)": poa_conventional_mttr,
        "Automation MTTR (hrs)": poa_automation_mttr,
    }
    poa_df = pd.DataFrame(list(poa_data.items()), columns=["Metric", "Value"])
    

    # Example data (replace with actual calculations)
    def highlight_met(val):
        if val == "Yes":
            return "background-color: #b6fcb6; color: black;"  # light green
        return ""

    metrics = {
        "Metric": [
            "Automation Defects",
            "Automation Wait Time",
            "Automation MTTR",
        ],
        "POA": [
            f" {int(round(poa_tsg_defects))}%",
            f"{int(round(poa_automation_wait))}%",
            f"{int(round(poa_automation_mttr))} Hrs"
        ],
        "Quarterly Average": [
            f" {int(round(st.session_state.actual_auto_defects))}%",
            f"{int(round(st.session_state.actual_automation_wait))}%",
            f"{int(round(st.session_state.actual_mttr))} Hrs",
        ],

        "Met": [
            "Yes" if st.session_state.actual_auto_defects <= poa_tsg_defects else "No",
            "Yes" if st.session_state.actual_automation_wait >= poa_automation_wait else "No",
            "Yes" if st.session_state.actual_mttr <= poa_automation_mttr else "No",
        ]
    }
    metrics_df = pd.DataFrame(metrics)
    
    c1, c2 = st.columns(2)
    with c1:
        st.header("Health Check")

        st.dataframe(
        metrics_df.style.applymap(highlight_met, subset=["Met"]),
        use_container_width=True,
    
        
    )
        st.image("images/poa1.png"),
        st.warning("Need SMC and SQL for historical data"),
    with c2:
        st.header("Call Center Metrics")
        load_digium_kpi(df) 
        st.divider()
        st.header("Incident Metrics")
        smc_metrics()
        



   

def donut_automated_hold():
    st.write("Hold times for UPS Automation Agents (ext. 901)")
    donut_hold_time_breakdown(901) #This is Correct Ext.
def donut_cbre_hold():
    st.write("Hold times for CBRE Agents \n 304 = SFR Agents, 316 = Legacy Agents")
    donut_hold_time_breakdown(316)
    donut_hold_time_breakdown(304) #2 CBRE 304 and 316
def donut_managers_hold():
    st.write("Hold times for UPS BaSE Managers")
    st.write("854 = Manager Critical, 910 = GTSG Escalation")
    donut_hold_time_breakdown(854)
    donut_hold_time_breakdown(910)
    
def donut_all_lines_holds():
    c1, c2 = st.columns(2)
    with c1:
        donut_hold_time_breakdown(901)
        st.write("Hold times for UPS Automation Agents (ext. 901)")

    with c2:
        donut_hold_time_breakdown("CBRE")
        st.write("Combined CBRE 304 + 316")
        st.info("CBRE Auto answers; hold time should be short")
    











# --- 5. Charting Functions  ---
def gt_2_traverse():
    df = st.session_state.get("df_filtered")
    if df is None or df.empty or "Traversed" not in df.columns:
        st.info("No data available or 'Traversed' column missing.")
        return

    def semicolon_count_exclude_999(traversed):
        if pd.isna(traversed) or "queue" not in str(traversed).lower():
            return 0
        queues = [q.strip() for q in str(traversed).split(";") if "queue" in q.lower()]
        queues_ex_999 = [q for q in queues if "999" not in q]
        return len(queues_ex_999) - 1 if len(queues_ex_999) > 1 else 0

    def list_queues_exclude_999(traversed):
        if pd.isna(traversed) or "queue" not in str(traversed).lower():
            return ""
        return ", ".join([
            q.strip() for q in str(traversed).split(";")
            if q.strip() and "queue" in q.lower() and "999" not in q
        ])

    df = df.copy()
    df["Semicolon Count Excl 999"] = df["Traversed"].apply(semicolon_count_exclude_999)

    # Aggregate by Call ID: sum hold/talk times, max semicolon count, concatenate queues, get first Start Time
    agg_df = df.groupby("Call ID").agg({
        "Hold Time (s)": "sum",
        "Talk Duration": "sum",
        "Semicolon Count Excl 999": "max",
        "Traversed": lambda x: ";".join([str(i) for i in x if pd.notna(i)]),
        "Start Time": "min"
    }).reset_index()

    # Only keep calls with 2 or more queues traversed (excluding 999)
    df_gt2 = agg_df[agg_df["Semicolon Count Excl 999"] >= 2].copy()

    #st.metric("Unique Calls Traversed ≥2 Queues (excluding 999)", value=len(df_gt2))

    with st.expander("Call Details - Unique calls that traversed 2+ queues"):
        if df_gt2.empty:
            st.write("No unique calls traversed 2 or more queues (excluding 999).")
            return

        df_gt2["Queues Traversed"] = df_gt2["Traversed"].apply(list_queues_exclude_999)
        df_gt2["Total Call Time (min)"] = (
            pd.to_numeric(df_gt2.get("Hold Time (s)", 0), errors="coerce").fillna(0) +
            pd.to_numeric(df_gt2.get("Talk Duration", 0), errors="coerce").fillna(0)
        ) / 60
        df_gt2["Total Hold Time (min)"] = pd.to_numeric(df_gt2.get("Hold Time (s)", 0), errors="coerce").fillna(0) / 60
        df_gt2["Day of Week"] = pd.to_datetime(df_gt2["Start Time"]).dt.day_name()
        df_gt2["Call Time"] = pd.to_datetime(df_gt2["Start Time"]).dt.strftime("%H:%M:%S")

        st.dataframe(
            df_gt2[[
                "Call ID",
                "Total Call Time (min)",
                "Total Hold Time (min)",
                "Semicolon Count Excl 999",
                "Queues Traversed",
                "Day of Week",
                "Call Time"
            ]],
            use_container_width=False
        )
    c1, c2 = st.columns(2)
    with c1:
  
        st.metric("Unique Calls Traversed ≥2 Queues (excluding 999)", value=len(df_gt2))
    
    
    # Metric: Total call time of all calls NOT in df_gt2 (calls with 2 or fewer transfers)
    df_le2 = agg_df[agg_df["Semicolon Count Excl 999"] <= 1].copy()
    total_call_time_le2 = df_le2["Hold Time (s)"].fillna(0) + df_le2["Talk Duration"].fillna(0)
    
    st.metric("Avg. Total Call Time >2 transfers (min)", f"{df_gt2['Total Call Time (min)'].mean():.2f}")
       
    
    # Metric: Total hold time for all calls with 2 or fewer transfers
    total_hold_time_le2 = df_le2["Hold Time (s)"].fillna(0).sum() / 60
    #st.metric(
    #    "Total Hold Time (min) for Calls with ≤2 Transfers",
    #    f"{total_hold_time_le2:.2f}"
    #)
    ca,cb,cc = st.columns(3)
    with ca:
        pass
    with cb:
        # Metric: Avg hold time for calls with 2 or fewer transfers
        avg_hold_time_le2 = (
        total_hold_time_le2 / len(df_le2)
        if len(df_le2) > 0 else 0
    )
    st.metric(
        "Avg Hold Time (min) for Calls with ≤2 Transfers",
        f"{avg_hold_time_le2:.2f}"
    )

    # Metric: Avg hold time for calls with more than 2 transfers
    total_hold_time_gt2 = df_gt2["Hold Time (s)"].fillna(0).sum() / 60
    avg_hold_time_gt2 = (
        total_hold_time_gt2 / len(df_gt2)
        if len(df_gt2) > 0 else 0
    )
    st.metric(
        "Avg Hold Time (min) for Calls with >2 Transfers",
        f"{avg_hold_time_gt2:.2f}"
    )
    with cc:
        pass
    with c2:
        st.info("How many unique calls traversed 2+ queues (excluding 999, by semicolon count, only if entry contains 'queue'). Aggregates across all roles with the same Call ID and sums hold times.")

    d1, d2, d3 = st.columns(3)

    with d1:

        # Bar graph: Total number of calls (≤2 vs >2 transfers) with hold times as y-axis
        count_data = pd.DataFrame({
            "Transfer Group": ["≤2 Transfers", ">2 Transfers"],
            "Call Count": [len(df_le2), len(df_gt2)],
            "Total Hold Time (min)": [total_hold_time_le2, total_hold_time_gt2]
        })
        fig_count_hold = px.bar(
            count_data,
            x="Transfer Group",
            y="Total Hold Time (min)",
            title="Total Hold Time by Transfer Group",
            text="Call Count",
            color="Transfer Group",
            color_discrete_sequence=UPS_COLORS
        )
        st.plotly_chart(fig_count_hold, use_container_width=True)
    with d2:
        # Create a pie chart of the number of queues traversed for all calls
        queue_counts = agg_df["Semicolon Count Excl 999"].value_counts().sort_index()
        queue_counts_df = queue_counts.reset_index()
        queue_counts_df.columns = ["# Queues Traversed (Excl 999)", "Call Count"]
        fig_queues = px.pie(
            queue_counts_df,
            names="# Queues Traversed (Excl 999)",
            values="Call Count",
            title="Distribution of Number of Queues Traversed (Excl 999)",
            hole=0.4,
            color_discrete_sequence=UPS_COLORS
        )
        st.plotly_chart(fig_queues, use_container_width=True)
    with d3:

        # Create a pie chart of the total hold time for all calls, and what percent of that comes from calls with more than 2 transfers
        total_hold_time_gt2 = df_gt2["Hold Time (s)"].sum()
        total_hold_time_le2 = df_le2["Hold Time (s)"].sum()
        hold_time_pie_df = pd.DataFrame({
            "Group": [">2 Transfers", "≤2 Transfers"],
            "Total Hold Time (min)": [total_hold_time_gt2 / 60, total_hold_time_le2 / 60]
        })
        fig_hold_time = px.pie(
            hold_time_pie_df,
            names="Group",
            values="Total Hold Time (min)",
            title="Total Hold Time: >2 Transfers vs ≤2 Transfers",
            hole=0.4,
            color_discrete_sequence=UPS_COLORS
        )
        st.plotly_chart(fig_hold_time, use_container_width=True)
def calls_by_day_bar():
    #sAverage number of calls by day selected (using global date range filter)
    df = st.session_state.get("df_filtered")
    if df is None or df.empty:
        st.write("No data available for the selected filters.")
        return

    # Use the date range from the global filter selections
    filter_selections = st.session_state.get("filter_selections", {})
    if "Date Range" in filter_selections:
        start_date_str, end_date_str = filter_selections["Date Range"]
        start_date = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime(end_date_str)
        df = df[(df["Start Time"].dt.date >= start_date.date()) & (df["Start Time"].dt.date <= end_date.date())]

    df["DayOfWeek"] = pd.Categorical(df["DayOfWeek"], categories=[
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ], ordered=True)
    calls_by_day = df.groupby("DayOfWeek").size().reset_index(name='Call Count')
    fig = px.bar(
        calls_by_day,
        x='DayOfWeek',
        y='Call Count',
        title='Average Calls by Day of Week',
        color='Call Count',
        color_discrete_map=UPS_COLORS
    )
    st.plotly_chart(fig, use_container_width=True)
    return fig
def chart_calls_by_category(df):
    """Creates a pie chart of calls by category."""
    if df.empty: return None
    counts = df['Call Category'].value_counts().reset_index()
    fig = px.pie(counts, names='Call Category', values='count', title='Calls by Category',
                 hole=0.4, color_discrete_sequence=UPS_COLORS)
    return fig
def generate_performance_pdf(kpi_data, charts):
    """Generates a PDF report from performance data and charts."""
    try:
        with open("images/upslogo.png", "rb") as f:
            logo_encoded = base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        logo_encoded = ""
    css = """<style> body { font-family: sans-serif; } h1, h2 { color: #3A201F; } h1 { text-align: center; border-bottom: 2px solid #ccc; } .kpi-container { display: flex; justify-content: space-around; padding: 20px 0; background-color: #f9f9f9; } .kpi-metric { text-align: center; } .kpi-value { font-size: 24px; font-weight: bold; } .kpi-label { font-size: 14px; } .chart-container { margin-top: 30px; page-break-inside: avoid; } img.logo { height: 50px; display: block; margin: auto; } </style>"""
    html = f"<html><head>{css}</head><body>"
    if logo_encoded: html += f'<img src="data:image/png;base64,{logo_encoded}" class="logo">'
    html += f"<h1>Call Center Performance Report</h1><h3>Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}</h3><h2>Key Metrics</h2><div class='kpi-container'>"
    for label, value in kpi_data.items():
        html += f"<div class='kpi-metric'><div class='kpi-value'>{value}</div><div class='kpi-label'>{label}</div></div>"
    html += "</div>"
    for title, fig in charts.items():
        fig.update_layout(colorway=UPS_COLORS)
        #img_bytes = fig.to_image(format="png", scale=2, engine="kaleido")
        #img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        #html += f"<div class='chart-container'><h2>{title}</h2><img src='data:image/png;base64,{img_base64}' style='width: 100%;'></div>"
    html += "</body></html>"
    #return HTML(string=html).write_pdf()

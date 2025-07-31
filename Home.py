# Home.py 
#cd "C:\Users\BNH0SRP\Call Center Project\Call_Center_Dashboard"
#python -m streamlit run Home.py
#vsecrets.toml:

"""[connections.mysql]
dialect = "mysql"
host = "10.234.34.225"
port = 42311
database = "Unnamed"
username = "anya"
password = "anya"
query = { charset = "utf8mb4 }"""
import streamlit as st 
#import mysql.connector
import pandas as pd 
from datetime import date 
from utils import ( 
    process_uploaded_file, 
    load_agent_mapping_from_file, 
    create_global_sidebar, 
    display_active_filters, 
    
    REQUIRED_COLUMNS, 
    # Assuming these functions are in utils.py and accept a dataframe 
    # table_call_data_preview, 
    # bar_v1 
) 
from smc import(
    smc_form,
    smc
)
# Set page configuration once at the start of the app's main script 
st.set_page_config( 
    page_title="BaSE Call Center Dashboard", 
    layout="wide", 
    page_icon="images/upslogo.png" 
) 
create_global_sidebar()
# --- Function to initialize all session state variables --- 
def initialize_session_state(): 
    # This function ensures all necessary keys exist in the session state 
    # when the app is first started. 
    defaults = { 
        'df_original': None, 
        'df_filtered': None, 
        'agent_map_custom': None, 
        'call_data_uploaded': False, 
        # Using your specified, detailed POA targets from your original file 
        'poa_conventional_defects': 5.0, 
        'poa_tsg_defects': 5.0, 
        'poa_base_defects': 5.0, 
        'poa_facility_sfr': 90.0, 
        'poa_automation_wait': 90.0, 
        'poa_conventional_mttr': 2.0, 
        'poa_automation_mttr': 1.0,
        'actual_mttr': 1, 
        'actual_tsg_defects': 5,
        'actual_automation_wait': 90,        
    } 
    for key, value in defaults.items(): 
        if key not in st.session_state: 
            st.session_state[key] = value 
# Run the initialization 
initialize_session_state() 
# --- Page Title and Logo --- 
c1, c2 = st.columns([0.1, 0.9]) 
with c1: 
    st.image("images/upslogo.png", width=80) 
with c2: 
    st.title("BaSE Call Center Dashboard")
st.markdown("### United Parcel Service Building and Systems Engineering (BaSE) Corporate Call Center")
# --- Introductory Content and Guides from your original file --- 
st.markdown("This locally hosted dashboard is built for secure performance and operations tracking across BaSE call center and ticket resolution data.") 
st.info(f"Today is **{date.today().strftime('%A, %B %d, %Y')}**.") 
with st.expander("How to Use This Dashboard"): 
    st.markdown(""" 
    - **Upload Data:** Use the `Upload Data Files` section below to load your Digium call data. You can also provide an optional agent mapping file. 
    - **Configure Targets:** Use the 'Update Targets (POA)' section to updpate set dashboard-wide goals. 
    - **Filter Data:** Use the sidebar on the left to filter the loaded data. These filters apply to all analytical pages. 
    - **Explore Pages:** Navigate to the `Operations`, `Performance`, or `Custom Report` pages in the sidebar to view the analysis. 
    """) 
# --- Main Page Layout --- 
st.divider() 
col_upload, col_settings = st.columns([0.2, 0.8]) 
with col_upload: 
    st.subheader("1. Upload Data Files") 
    call_file = st.file_uploader("Upload Digium Call Data", type=["csv"]) 
    
    if call_file: 
        st.session_state['df_original'] = process_uploaded_file(call_file) 
    

    with st.expander("Optional Settings"):
        #st.subheader("Optional: Update Targets (POA)", help = "POA stands for Point of Arrival. These are the key performance targets that apply to all analytical pages.")
     
    
        with st.form(key = "Staff"):
            st.number_input("Number of Shifts Week Ending", help= "Enter the number of shifts from Teams Shift app", min_value=0, max_value=100, value=70, key='num_shifts') 
            if st.form_submit_button("Save Data and Generate Report"):
                st.session_state['actual_staff_for_week'] = st.session_state['num_shifts']
                st.success("Staff data saved!")
        ticket_file = st.file_uploader("Upload SMC Ticket Data (Optional)", type=["csv"])
        template_csv = pd.DataFrame(columns=list(REQUIRED_COLUMNS)).to_csv(index=False).encode('utf-8') 
        mapping_file = st.file_uploader("Upload Agent-Extension Mapping File (Optional)", type=["xlsx"], accept_multiple_files=False)
        if mapping_file:
            try:
                st.session_state['agent_map_custom'] = load_agent_mapping_from_file(mapping_file)
            except Exception as e:
                st.error(f"Error reading agent mapping file: {e}")
        with st.form(key='poa_form'): 
            col1, col2 = st.columns(2) 
            with col1: 
                #conv_defects = st.number_input("Conventional Defects (%)", value=st.session_state.poa_conventional_defects) 
                tsg_defects = st.number_input("TSG Defects (%)", value=st.session_state.poa_tsg_defects, help = "TSG Technical Support Group") 
                #conv_mttr = st.number_input("Conventional MTTR (hrs)", value=st.session_state.poa_conventional_mttr) 
                auto_wait = st.number_input("Automation Wait Time (0-5min) (%)", value=st.session_state.poa_automation_wait) 
    
            with col2: 
                #sfr_wait = st.number_input("Facility SFR Wait Time (0-5min) (%)", value=st.session_state.poa_facility_sfr) 
                base_defects = st.number_input("BaSE Defects (%)", value=st.session_state.poa_base_defects) 

                auto_mttr = st.number_input("Automation MTTR (hrs)", value=st.session_state.poa_automation_mttr, help = "MTTR Mean Time to Resolution") 
                
                
            if st.form_submit_button('Save POA Settings'): 
                st.session_state.poa_tsg_defects = tsg_defects 
                st.session_state.poa_base_defects = base_defects 
                st.session_state.poa_automation_wait = auto_wait 
                st.session_state.poa_automation_mttr = auto_mttr 
                st.success("POA settings saved!")
    
with col_settings: 
    smc_form()
    
     
st.divider() 
# --- Data Preview Section --- 
c1, c2, c3 = st.columns([0.5, 0.3, 0.2])
with c1:
    df_preview = st.session_state.get("df_filtered") 
    # The call_data_uploaded key is now initialized in initialize_session_state()
    if df_preview is not None and not df_preview.empty: 
        display_active_filters() # Show which filters are applied 

    # You can add a preview chart here if you have a simple one, like bar_v1 
    # For example: bar_v1(df_preview) 
    elif st.session_state.get("df_original") is not None:
        st.info('Your data has been loaded. Use the sidebar to apply filters and preview the data.')
        # Set a session state flag if call data is uploaded
        st.session_state['call_data_uploaded'] = True
    else: 
        st.warning('No Call Data: Please upload your main call data file in "Upload Digium Data" to activate the dashboard.') 

with c2:
    with st.expander("Preview SMC Data"):
        smc()
with c3:
    st.subheader("Database Connection")
    # Initialize connection.
    conn = st.connection('mysql', type='sql')
    # Check if the connection is established
    if conn is None:
        st.error("Failed to connect to the SQL database. Please check your connection settings to enable historical trends")
    # Perform query.
    df = conn.query('SELECT * FROM pets;', ttl=600)
    
    if df is not None and not df.empty:
        st.success("Data loaded successfully from SQL database.")
    else:
        st.warning("No data found in the SQL database. Please check your connection and query for historical trends.")
    

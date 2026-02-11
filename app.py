import streamlit as st
from streamlit_calendar import calendar
from github import Github
import json
from datetime import datetime, timedelta

# --- Configuration ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "controlswmi-pixel/Controls-Calendar"
FILE_PATH = "schedule.json"

# --- Team Members ---
TEAM_MEMBERS = [
    "Carson", "Dave Miller", "Andrew Roberts", "Christopher Smith",
    "Eric Zelt", "Kent Bearman", "Larry Ley", "Moses Ward", "Scott McNamara"
]

# --- Professional Color Palette ---
CATEGORY_COLORS = {
    "Panel Build": "#0078D4",      # Outlook Blue
    "Vacation": "#107C10",         # Excel Green
    "On-Site Startup": "#D13438",  # Office Red
    "Office Day": "#FF8C00",       # Orange
    "Maintenance": "#881798"       # Purple
}

# --- 1. Global Page CSS (Layout & Sidebar) ---
def inject_page_css():
    st.markdown("""
        <style>
            /* Maximize main content area */
            .block-container {
                padding-top: 0.5rem !important;
                padding-bottom: 0rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                max-width: 100% !important;
            }
            
            /* Hide Streamlit Header & Footer */
            header {visibility: hidden;}
            footer {visibility: hidden;}
            #MainMenu {visibility: hidden;}
            
            /* Sidebar styling */
            [data-testid="stSidebar"] {
                min-width: 350px;
                max-width: 350px;
            }
            
            /* Sidebar Form styling */
            [data-testid="stForm"] {
                border: 1px solid #444;
                padding: 20px;
                border-radius: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

# --- 2. Calendar Component CSS (The Fix for Height) ---
CALENDAR_CSS = """
    /* Force the calendar container to take up 85% of the viewport height */
    .fc {
        height: 85vh !important;
    }
    
    /* Improve the look of the event bars */
    .fc-event {
        cursor: pointer;
        padding: 2px 4px;
        font-size: 0.9rem;
        border: none !important;
    }
    
    /* Ensure the grid cells stretch to fill the height */
    .fc-view-harness {
        height: 100% !important;
    }
"""

def load_data_from_github():
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        return json.loads(contents.decoded_content.decode()), contents.sha
    except Exception as e:
        return [], None

def save_data_to_github(new_data, sha):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)
    repo.update_file(path=FILE_PATH, message="Update schedule", content=json.dumps(new_data, indent=4), sha=contents.sha)

def check_conflicts(new_event, current_schedule):
    new_start = datetime.strptime(new_event['start'], "%Y-%m-%d")
    new_end = datetime.strptime(new_event['end'], "%Y-%m-%d")
    conflicts = []
    for event in current_schedule:
        if event['resourceId'] == new_event['resourceId']:
            existing_start = datetime.strptime(event['start'], "%Y-%m-%d")
            existing_end = datetime.strptime(event['end'], "%Y-%m-%d")
            if new_start < existing_end and new_end > existing_start:
                conflicts.append(f"Conflict: {event['title']}")
    return conflicts

# --- Main Application ---
st.set_page_config(page_title="Controls Schedule", layout="wide")
inject_page_css()

# Load Data
schedule_data, file_sha = load_data_from_github()

# --- Sidebar: Form ---
with st.sidebar:
    st.markdown("### 📅 Scheduler")
    
    with st.form("add_event_form", clear_on_submit=True):
        st.caption("Create New Entry")
        
        # 1. Title
        title = st.text_input("Project / Item Name", placeholder="e.g. Line 4 Commissioning")
        
        # 2. Assignee & Type
        assignee = st.selectbox("Assignee", TEAM_MEMBERS)
        category = st.selectbox("Activity Type", list(CATEGORY_COLORS.keys()))
        
        st.write("") 
        
        # 3. Dates
        c1, c2 = st.columns(2)
        start_date = c1.date_input("Start", value="today")
        end_date = c2.date_input("End", value="today")
        
        st.write("")
        
        # 4. Submit
        submitted = st.form_submit_button("Add to Schedule", use_container_width=True)
        
        if submitted:
            if start_date > end_date:
                st.error("End date must be after start date.")
            else:
                adjusted_end = end_date + timedelta(days=1)
                new_event = {
                    "title": f"{assignee}: {title}",
                    "start": str(start_date),
                    "end": str(adjusted_end),
                    "resourceId": assignee,
                    "backgroundColor": CATEGORY_COLORS[category],
                    "borderColor": CATEGORY_COLORS[category],
                    "extendedProps": {"category": category, "assignee": assignee}
                }
                
                conflicts = check_conflicts(new_event, schedule_data)
                if conflicts:
                    st.error(f"Conflict: {assignee} is already booked!")
                else:
                    schedule_data.append(new_event)
                    save_data_to_github(schedule_data, file_sha)
                    st.success("Added!")
                    st.rerun()

# --- Main Calendar View ---
calendar_options = {
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,listMonth"
    },
    "initialView": "dayGridMonth",
    "selectable": True,
    "editable": False,
    "navLinks": True,
    # We remove the height setting here and rely on custom_css below
}

# Pass the custom CSS directly to the component
calendar(
    events=schedule_data, 
    options=calendar_options, 
    custom_css=CALENDAR_CSS
)

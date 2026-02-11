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

# --- CSS: Layout & Text Wrapping ---
def inject_page_css():
    st.markdown("""
        <style>
            /* 1. Maximize Main View */
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 0rem !important;
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                max-width: 100% !important;
            }
            
            /* 2. Hide Streamlit Elements */
            header {visibility: hidden;}
            footer {visibility: hidden;}
            
            /* 3. Sidebar Styling */
            [data-testid="stSidebar"] {
                min-width: 350px;
                max-width: 350px;
                background-color: #f8f9fa; /* Light contrast */
            }
            
            /* 4. Calendar Text Wrapping (Fixes the "..." issue) */
            .fc-event-title {
                white-space: normal !important;
                overflow: hidden !important;
                text-overflow: clip !important;
                font-size: 0.85rem !important;
            }
            
            /* 5. Custom Button Styling */
            div.stButton > button {
                width: 100%;
                background-color: #0078D4;
                color: white;
                border: none;
                padding: 10px;
            }
            div.stButton > button:hover {
                background-color: #005a9e;
                color: white;
            }
        </style>
    """, unsafe_allow_html=True)

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

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 📅 Team Scheduler")
    st.markdown("---")
    
    with st.form("add_event_form", clear_on_submit=True):
        st.markdown("**1. Project Details**")
        title = st.text_input("Description", placeholder="e.g. Line 4 Commissioning")
        
        c_assign, c_type = st.columns([1.5, 1])
        assignee = c_assign.selectbox("Assignee", TEAM_MEMBERS)
        category = c_type.selectbox("Type", list(CATEGORY_COLORS.keys()))
        
        st.markdown("---")
        st.markdown("**2. Duration**")
        
        c_start, c_end = st.columns(2)
        start_date = c_start.date_input("Start", value="today")
        end_date = c_end.date_input("End", value="today")
        
        st.write("")
        submitted = st.form_submit_button("Add Entry")
        
        if submitted:
            if start_date > end_date:
                st.error("Invalid dates.")
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
                    st.error(f"Conflict detected for {assignee}!")
                else:
                    schedule_data.append(new_event)
                    save_data_to_github(schedule_data, file_sha)
                    st.success("Added!")
                    st.rerun()

# --- Calendar View ---
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
    
    # FIX: Robust Height Setting
    "height": "750px",       # Fixed pixel height guarantees it won't disappear
    "expandRows": True,      # Stretches rows to fill that 750px
    "handleWindowResize": True,
}

calendar(events=schedule_data, options=calendar_options)

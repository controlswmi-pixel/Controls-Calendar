import streamlit as st
from streamlit_calendar import calendar
from github import Github
import json
from datetime import datetime, timedelta

# --- Configuration ---
# Your repo details
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "controlswmi-pixel/Controls-Calendar" 
FILE_PATH = "schedule.json"

# --- Team Members (From your screenshot) ---
TEAM_MEMBERS = [
    "Carson",
    "Dave Miller",
    "Andrew Roberts",
    "Christopher Smith",
    "Eric Zelt",
    "Kent Bearman",
    "Larry Ley",
    "Moses Ward",
    "Scott McNamara"
]

# --- Professional Color Palette (Outlook-style) ---
CATEGORY_COLORS = {
    "Panel Build": "#0078D4",      # Outlook Blue
    "Vacation": "#107C10",         # Excel Green
    "On-Site Startup": "#D13438",  # Office Red
    "Office Day": "#FF8C00",       # Orange
    "Maintenance": "#881798"       # Purple
}

# --- CSS for "Single Screen" View ---
# This removes the massive white bar at the top and reduces side padding
def inject_custom_css():
    st.markdown("""
        <style>
            /* Remove top white bar and reduce padding */
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 0rem !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
                max-width: 100% !important;
            }
            /* Hide the default Streamlit header/hamburger menu space */
            header {visibility: hidden;}
            /* Adjust sidebar width if needed */
            [data-testid="stSidebar"] {
                min-width: 300px;
                max-width: 300px;
            }
        </style>
    """, unsafe_allow_html=True)

def load_data_from_github():
    """Fetches the JSON file from the repo."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        return json.loads(contents.decoded_content.decode()), contents.sha
    except Exception as e:
        st.error(f"GitHub Connection Error: {e}")
        return [], None

def save_data_to_github(new_data, sha):
    """Pushes the updated JSON back to the repo."""
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)
    
    repo.update_file(
        path=FILE_PATH,
        message="Update schedule",
        content=json.dumps(new_data, indent=4),
        sha=contents.sha
    )

def check_conflicts(new_event, current_schedule):
    new_start = datetime.strptime(new_event['start'], "%Y-%m-%d")
    new_end = datetime.strptime(new_event['end'], "%Y-%m-%d")
    
    conflicts = []
    for event in current_schedule:
        if event['resourceId'] == new_event['resourceId']:
            existing_start = datetime.strptime(event['start'], "%Y-%m-%d")
            existing_end = datetime.strptime(event['end'], "%Y-%m-%d")
            
            # Simple overlap check
            if new_start < existing_end and new_end > existing_start:
                conflicts.append(f"Conflict: {event['title']}")
    
    return conflicts

# --- Main Application ---
st.set_page_config(page_title="Controls Schedule", layout="wide")
inject_custom_css()

# Load Data
schedule_data, file_sha = load_data_from_github()

# --- Sidebar: Quick Entry ---
with st.sidebar:
    st.markdown("### New Schedule Item") # Clean header, no emoji
    
    with st.form("add_event_form", clear_on_submit=True): # clear_on_submit makes it faster to add multiple
        title = st.text_input("Project / Description")
        
        # Split into two columns for compact look
        c1, c2 = st.columns(2)
        assignee = c1.selectbox("Who", TEAM_MEMBERS)
        category = c2.selectbox("Type", list(CATEGORY_COLORS.keys()))
        
        c3, c4 = st.columns(2)
        start_date = c3.date_input("Start", value="today")
        end_date = c4.date_input("End", value="today")
        
        submitted = st.form_submit_button("Add Item", use_container_width=True)
        
        if submitted:
            if start_date > end_date:
                st.error("Error: End date must be after start date.")
            else:
                # FullCalendar requires exclusive end date (so we add 1 day)
                adjusted_end = end_date + timedelta(days=1)
                
                new_event = {
                    "title": f"{assignee} - {title}",
                    "start": str(start_date),
                    "end": str(adjusted_end),
                    "resourceId": assignee,
                    "backgroundColor": CATEGORY_COLORS[category],
                    "borderColor": CATEGORY_COLORS[category],
                    "extendedProps": {
                        "category": category,
                        "assignee": assignee
                    }
                }
                
                conflicts = check_conflicts(new_event, schedule_data)
                
                if conflicts:
                    st.error(f"Conflict detected for {assignee}!")
                else:
                    schedule_data.append(new_event)
                    save_data_to_github(schedule_data, file_sha)
                    st.success("Saved")
                    st.rerun()

# --- Main Calendar View ---

# Calendar Configuration
calendar_options = {
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,listMonth" 
    },
    "initialView": "dayGridMonth",
    "selectable": True,
    "editable": False, # Keep read-only on drag to prevent accidental shifts for now
    "navLinks": True,
    "height": "85vh", # FORCE HEIGHT to 85% of viewport height (Single Screen)
    "contentHeight": "auto",
}

# Render Calendar
calendar(events=schedule_data, options=calendar_options)

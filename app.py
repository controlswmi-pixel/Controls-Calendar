import streamlit as st
from streamlit_calendar import calendar
from github import Github
import json
import pandas as pd
from datetime import datetime, timedelta

# --- Configuration ---
# You will set these in Streamlit Secrets later
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "your-username/controls-team-scheduler" # CHANGE THIS
FILE_PATH = "schedule.json"

# --- Color Mapping for your "Legend" ---
CATEGORY_COLORS = {
    "Panel Build": "#3B82F6",  # Blue
    "Vacation": "#10B981",     # Green
    "On-Site Startup": "#EF4444", # Red
    "Office Day": "#F59E0B",   # Orange
    "Maintenance": "#6B7280"   # Gray
}

def load_data_from_github():
    """Fetches the JSON file from the repo."""
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)
    return json.loads(contents.decoded_content.decode()), contents.sha

def save_data_to_github(new_data, sha):
    """Pushes the updated JSON back to the repo."""
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)
    
    # Update the file
    repo.update_file(
        path=FILE_PATH,
        message="Update schedule via Streamlit",
        content=json.dumps(new_data, indent=4),
        sha=contents.sha
    )

def check_conflicts(new_event, current_schedule):
    """Checks if the assignee is already booked for these dates."""
    new_start = datetime.strptime(new_event['start'], "%Y-%m-%d")
    new_end = datetime.strptime(new_event['end'], "%Y-%m-%d")
    
    conflicts = []
    for event in current_schedule:
        # Only check conflicts for the same person
        if event['resourceId'] == new_event['resourceId']:
            existing_start = datetime.strptime(event['start'], "%Y-%m-%d")
            existing_end = datetime.strptime(event['end'], "%Y-%m-%d")
            
            # Overlap logic
            if new_start < existing_end and new_end > existing_start:
                conflicts.append(f"Conflict with: {event['title']} ({event['start']} to {event['end']})")
    
    return conflicts

# --- Main App Layout ---
st.set_page_config(page_title="Controls Team Scheduler", layout="wide")
st.title("🛠️ Controls & Automation Team Schedule")

# Load Data
try:
    schedule_data, file_sha = load_data_from_github()
except Exception as e:
    st.error(f"Error loading data: {e}")
    schedule_data = []

# --- Sidebar: Add New Event ---
with st.sidebar:
    st.header("Add New Schedule Item")
    with st.form("add_event_form"):
        title = st.text_input("Project / Item Name")
        assignee = st.selectbox("Assignee", ["Carson", "Tech A", "Tech B", "Tech C"])
        category = st.selectbox("Activity Type", list(CATEGORY_COLORS.keys()))
        
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start Date")
        end_date = col2.date_input("End Date")
        
        submitted = st.form_submit_button("Add to Schedule")
        
        if submitted:
            new_event = {
                "title": f"{assignee}: {title}",
                "start": str(start_date),
                "end": str(end_date + timedelta(days=1)), # FullCalendar is exclusive on end date
                "resourceId": assignee, # Used for grouping
                "backgroundColor": CATEGORY_COLORS[category],
                "borderColor": CATEGORY_COLORS[category],
                "extendedProps": {
                    "category": category,
                    "assignee": assignee
                }
            }
            
            conflicts = check_conflicts(new_event, schedule_data)
            
            if conflicts:
                st.error("🛑 Scheduling Conflict Detected!")
                for c in conflicts:
                    st.write(c)
            else:
                schedule_data.append(new_event)
                save_data_to_github(schedule_data, file_sha)
                st.success("Event added! Refreshing...")
                st.rerun()

# --- Main Calendar View ---
# Calendar Options
calendar_options = {
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,listMonth"
    },
    "initialView": "dayGridMonth",
    "selectable": True,
}

# Render Calendar
calendar(events=schedule_data, options=calendar_options)

# Legend
st.write("---")
cols = st.columns(len(CATEGORY_COLORS))
for idx, (cat, color) in enumerate(CATEGORY_COLORS.items()):
    cols[idx].markdown(f"**<span style='color:{color}'>█ {cat}</span>**", unsafe_allow_html=True)

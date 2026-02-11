import streamlit as st
from streamlit_calendar import calendar
from github import Github, Auth # Updated Import
import json
from datetime import datetime, timedelta

# --- Configuration ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "controlswmi-pixel/Controls-Calendar"
SCHEDULE_FILE = "schedule.json"
TEAM_FILE = "team.json"

# --- Default Team (Used if team.json doesn't exist yet) ---
DEFAULT_TEAM = [
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
            
            /* 3. Sidebar Styling - Removed the white background color */
            [data-testid="stSidebar"] {
                min-width: 350px;
                max-width: 350px;
            }
            
            /* 4. Calendar Text Wrapping */
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

# --- GitHub Helper Functions ---
def get_github_client():
    auth = Auth.Token(GITHUB_TOKEN) # Fixes the DeprecationWarning
    return Github(auth=auth)

def load_data(filename):
    """Generic function to load JSON from GitHub"""
    try:
        g = get_github_client()
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(filename)
        return json.loads(contents.decoded_content.decode()), contents.sha
    except Exception:
        return None, None

def save_data(filename, new_data, sha=None):
    """Generic function to save JSON to GitHub"""
    g = get_github_client()
    repo = g.get_repo(REPO_NAME)
    
    if sha:
        repo.update_file(path=filename, message=f"Update {filename}", content=json.dumps(new_data, indent=4), sha=sha)
    else:
        # Create file if it doesn't exist
        repo.create_file(path=filename, message=f"Create {filename}", content=json.dumps(new_data, indent=4))

# --- Main Application ---
st.set_page_config(page_title="Controls Schedule", layout="wide")
inject_page_css()

# 1. Load Team Data
team_data, team_sha = load_data(TEAM_FILE)
if not team_data:
    team_data = DEFAULT_TEAM # Fallback to default if file missing

# 2. Load Schedule Data
schedule_data, schedule_sha = load_data(SCHEDULE_FILE)
if not schedule_data:
    schedule_data = []

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 📅 Team Scheduler")
    
    # --- ADD EVENT SECTION ---
    with st.form("add_event_form", clear_on_submit=True):
        st.caption("New Schedule Entry")
        title = st.text_input("Description", placeholder="e.g. Line 4 Commissioning")
        
        c_assign, c_type = st.columns([1.5, 1])
        assignee = c_assign.selectbox("Assignee", team_data)
        category = c_type.selectbox("Type", list(CATEGORY_COLORS.keys()))
        
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
                
                # Basic Conflict Check
                conflict = False
                for event in schedule_data:
                    if event['resourceId'] == assignee:
                        ex_start = datetime.strptime(event['start'], "%Y-%m-%d")
                        ex_end = datetime.strptime(event['end'], "%Y-%m-%d")
                        new_s = datetime.strptime(str(start_date), "%Y-%m-%d")
                        new_e = datetime.strptime(str(adjusted_end), "%Y-%m-%d")
                        if new_s < ex_end and new_e > ex_start:
                            conflict = True
                            st.error(f"Conflict: {event['title']}")
                            break
                
                if not conflict:
                    schedule_data.append(new_event)
                    save_data(SCHEDULE_FILE, schedule_data, schedule_sha)
                    st.success("Added!")
                    st.rerun()

    st.write("---")

    # --- TEAM MANAGEMENT SECTION ---
    with st.expander("⚙️ Manage Team Members"):
        st.caption("Add or Remove team members here.")
        
        # Add Member
        new_member = st.text_input("New Member Name")
        if st.button("Add Member"):
            if new_member and new_member not in team_data:
                team_data.append(new_member)
                team_data.sort() # Keep alphabetical
                save_data(TEAM_FILE, team_data, team_sha)
                st.success(f"Added {new_member}")
                st.rerun()
            elif new_member in team_data:
                st.warning("Member already exists.")
        
        st.write("")
        
        # Remove Member
        member_to_remove = st.selectbox("Remove Member", ["Select..."] + team_data)
        if st.button("Remove Selected"):
            if member_to_remove != "Select...":
                team_data.remove(member_to_remove)
                save_data(TEAM_FILE, team_data, team_sha)
                st.success(f"Removed {member_to_remove}")
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
    "height": "750px", 
    "expandRows": True,
    "handleWindowResize": True,
}

calendar(events=schedule_data, options=calendar_options)

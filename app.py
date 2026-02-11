import streamlit as st
from streamlit_calendar import calendar
from github import Github, Auth
import json
from datetime import datetime, timedelta

# --- Configuration ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "controlswmi-pixel/Controls-Calendar"
SCHEDULE_FILE = "schedule.json"
TEAM_FILE = "team.json"

# --- Default Team ---
DEFAULT_TEAM = [
    "Carson", "Dave Miller", "Andrew Roberts", "Christopher Smith",
    "Eric Zelt", "Kent Bearman", "Larry Ley", "Moses Ward", "Scott McNamara"
]

# --- Color Palette ---
CATEGORY_COLORS = {
    "Panel Build": "#0078D4",      # Blue
    "Vacation": "#107C10",         # Green
    "On-Site Startup": "#D13438",  # Red
    "Office Day": "#FF8C00",       # Orange
    "Maintenance": "#881798"       # Purple
}

# --- CSS: The Bottom Dock & Layout ---
def inject_page_css():
    st.markdown("""
        <style>
            /* 1. Reset Main Container */
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 5rem !important; /* Make room for the dock */
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                max-width: 100% !important;
            }
            
            /* 2. Hide Standard Streamlit UI */
            header, footer, [data-testid="stSidebar"] {display: none !important;}
            
            /* 3. THE BOTTOM DOCK BAR */
            /* We target the specific horizontal block at the bottom of the script */
            [data-testid="stHorizontalBlock"]:last-of-type {
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                background-color: #1a1b21; /* Darker distinct background */
                border-top: 1px solid #333;
                padding: 10px 20px;
                z-index: 1000;
                gap: 10px; /* Spacing between buttons */
            }
            
            /* 4. Dock Buttons Styling */
            /* Target buttons specifically inside the dock to make them tall and bold */
            [data-testid="stHorizontalBlock"]:last-of-type button {
                height: 3rem;
                border: 1px solid #444;
                background-color: #262730;
                color: white;
                font-weight: 600;
                border-radius: 8px;
            }
            [data-testid="stHorizontalBlock"]:last-of-type button:hover {
                border-color: #0078D4;
                color: #0078D4;
                background-color: #2b2d35;
            }

            /* 5. Calendar Tweaks */
            .fc-event-title {
                white-space: normal !important;
                overflow: hidden !important;
                text-overflow: clip !important;
                font-size: 0.85rem !important;
            }
            
            /* 6. Team Manager List Styling */
            .team-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 8px;
                background-color: #262730;
                margin-bottom: 5px;
                border-radius: 5px;
            }
        </style>
    """, unsafe_allow_html=True)

# --- GitHub Helpers ---
def get_github_client():
    auth = Auth.Token(GITHUB_TOKEN)
    return Github(auth=auth)

def load_data(filename):
    try:
        g = get_github_client()
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(filename)
        return json.loads(contents.decoded_content.decode()), contents.sha
    except Exception:
        return None, None

def save_data(filename, new_data, sha=None):
    g = get_github_client()
    repo = g.get_repo(REPO_NAME)
    if sha:
        repo.update_file(path=filename, message=f"Update {filename}", content=json.dumps(new_data, indent=4), sha=sha)
    else:
        repo.create_file(path=filename, message=f"Create {filename}", content=json.dumps(new_data, indent=4))

# --- DIALOG: Add Event ---
@st.dialog("➕ New Schedule Item")
def add_event_dialog(team_list, schedule_data, schedule_sha):
    with st.form("add_event_form", clear_on_submit=True):
        title = st.text_input("Project / Description", placeholder="e.g. Line 4 Commissioning")
        
        c1, c2 = st.columns(2)
        assignee = c1.selectbox("Who", team_list)
        category = c2.selectbox("Type", list(CATEGORY_COLORS.keys()))
        
        c3, c4 = st.columns(2)
        start_date = c3.date_input("Start", value="today")
        end_date = c4.date_input("End", value="today")
        
        st.write("")
        if st.form_submit_button("Save Item", use_container_width=True):
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
                
                # Check Conflicts
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
                    st.rerun()

# --- DIALOG: Manage Team ---
@st.dialog("👥 Team Management")
def manage_team_dialog(current_team, team_sha):
    # 1. Quick Add at Top
    c_in, c_btn = st.columns([3, 1])
    new_name = c_in.text_input("New Member", label_visibility="collapsed", placeholder="Enter name...")
    if c_btn.button("Add", use_container_width=True):
        if new_name and new_name not in current_team:
            current_team.append(new_name)
            current_team.sort()
            save_data(TEAM_FILE, current_team, team_sha)
            st.rerun()
    
    st.divider()
    
    # 2. Clean List of Members with Delete Buttons
    st.caption(f"Current Team ({len(current_team)})")
    
    # Scrollable container for the list
    with st.container(height=300):
        for member in current_team:
            # Create a "Row" layout
            col_txt, col_del = st.columns([4, 1])
            col_txt.markdown(f"<div style='padding-top: 10px; font-size:16px;'>👤 <b>{member}</b></div>", unsafe_allow_html=True)
            
            # The trash button
            if col_del.button("🗑️", key=f"del_{member}", help=f"Remove {member}"):
                current_team.remove(member)
                save_data(TEAM_FILE, current_team, team_sha)
                st.rerun()

# --- Main App Logic ---
st.set_page_config(page_title="Controls Schedule", layout="wide", initial_sidebar_state="collapsed")
inject_page_css()

# Load Data
team_data, team_sha = load_data(TEAM_FILE)
if not team_data: team_data = DEFAULT_TEAM

schedule_data, schedule_sha = load_data(SCHEDULE_FILE)
if not schedule_data: schedule_data = []

# --- Render Calendar ---
calendar_options = {
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,listMonth"
    },
    "initialView": "dayGridMonth",
    "selectable": True,
    "editable": False,
    "height": "80vh", # Leaves just enough room for the dock
    "expandRows": True,
    "handleWindowResize": True,
}

calendar(events=schedule_data, options=calendar_options)

# --- THE BOTTOM DOCK ---
# This specific horizontal block is targeted by the CSS above to stick to the bottom
dock_col1, dock_col2, dock_col3 = st.columns(3)

if dock_col1.button("➕ Add Item", use_container_width=True):
    add_event_dialog(team_data, schedule_data, schedule_sha)

if dock_col2.button("👥 Team", use_container_width=True):
    manage_team_dialog(team_data, team_sha)

if dock_col3.button("🔄 Refresh", use_container_width=True):
    st.rerun()

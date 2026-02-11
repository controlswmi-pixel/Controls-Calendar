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

# --- CSS: Bottom Dock & Layout ---
def inject_page_css():
    st.markdown("""
        <style>
            /* 1. Hide Sidebar Completely */
            [data-testid="stSidebar"] {display: none;}
            section[data-testid="stSidebar"] {display: none;}
            
            /* 2. Hide Header/Footer */
            header {visibility: hidden;}
            footer {visibility: hidden;}
            
            /* 3. Maximize Screen Real Estate */
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 5rem !important; /* Space for bottom dock */
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                max-width: 100% !important;
            }
            
            /* 4. Calendar Styling */
            .fc-event-title {
                white-space: normal !important;
                overflow: hidden !important;
                text-overflow: clip !important;
                font-size: 0.85rem !important;
            }
            
            /* 5. Bottom Dock Container */
            .bottom-dock {
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                background-color: #262730; /* Dark mode match */
                border-top: 1px solid #444;
                padding: 15px 20px;
                z-index: 9999;
                text-align: center;
                box-shadow: 0px -2px 10px rgba(0,0,0,0.3);
            }
            
            /* 6. Action Buttons */
            div.stButton > button {
                width: 100%;
                border-radius: 8px;
                height: 3rem;
                font-weight: bold;
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
@st.dialog("➕ Add Schedule Item")
def add_event_dialog(team_list, schedule_data, schedule_sha):
    with st.form("add_event_form", clear_on_submit=True):
        title = st.text_input("Project / Description", placeholder="e.g. Line 4 Commissioning")
        
        c1, c2 = st.columns(2)
        assignee = c1.selectbox("Who", team_list)
        category = c2.selectbox("Type", list(CATEGORY_COLORS.keys()))
        
        c3, c4 = st.columns(2)
        start_date = c3.date_input("Start", value="today")
        end_date = c4.date_input("End", value="today")
        
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
                    st.success("Saved!")
                    st.rerun()

# --- DIALOG: Manage Team ---
@st.dialog("👥 Manage Team")
def manage_team_dialog(current_team, team_sha):
    st.caption("Add or remove members from the list below.")
    
    # 1. Add New Member Section
    c_input, c_btn = st.columns([3, 1])
    new_name = c_input.text_input("Add Name", label_visibility="collapsed", placeholder="New Member Name")
    if c_btn.button("Add", use_container_width=True):
        if new_name and new_name not in current_team:
            current_team.append(new_name)
            current_team.sort()
            save_data(TEAM_FILE, current_team, team_sha)
            st.rerun()
    
    st.divider()
    
    # 2. List of Current Members
    st.markdown("#### Current Team")
    # Using a container for the list so it scrolls if long
    with st.container(height=300):
        for member in current_team:
            col_name, col_del = st.columns([4, 1])
            col_name.write(f"👤 {member}")
            if col_del.button("❌", key=f"del_{member}"):
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
    "height": "75vh", # Leave room for bottom dock
    "expandRows": True,
    "handleWindowResize": True,
}

calendar(events=schedule_data, options=calendar_options)

# --- Render Bottom Dock ---
# We use a container placed after the calendar to act as the dock
st.write("") # Spacer
st.divider() # Visual separation

col_left, col_mid, col_right = st.columns([1, 2, 1])

with col_mid:
    # This creates the centered button row
    b1, b2, b3 = st.columns(3)
    
    if b1.button("➕ Add Item", use_container_width=True):
        add_event_dialog(team_data, schedule_data, schedule_sha)
        
    if b2.button("👥 Team", use_container_width=True):
        manage_team_dialog(team_data, team_sha)
        
    if b3.button("🔄 Refresh", use_container_width=True):
        st.rerun()

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Law Portal", page_icon="⚖️", layout="wide")

# --- 2. FIREBASE CONNECTION ---
# We use @st.cache_resource so it only connects to the database once
@st.cache_resource
def init_db():
    if not firebase_admin._apps:
        try:
            # First, try to load credentials from Streamlit Secrets (for Cloud Deployment)
            if "firebase" in st.secrets:
                # Convert the Streamlit secret AttrDict into a standard Python dictionary
                cert_dict = dict(st.secrets["firebase"])
                cred = credentials.Certificate(cert_dict)
            else:
                # Fallback to local file if secrets aren't found (for local PC development)
                cred = credentials.Certificate('firebase-key.json')
                
            firebase_admin.initialize_app(cred)
            return firestore.client()
        except Exception as e:
            # Silently fail here so the app still runs in mock data mode if no keys are found
            print(f"Database connection error: {e}")
            return None 
    return firestore.client()

db = init_db()

# --- MOCK DATA (Fallback if Firebase isn't connected yet) ---
MOCK_DATA = [
    {"module": "PVL3702", "subject": "myModules: forum digest", "content": "Announcement for online class...", "date": "2026-02-24", "isDeadline": False},
    {"module": "PVL3702", "subject": "Assignment One Available", "content": "The first assignment is due on 15 March.", "date": "2026-02-13", "isDeadline": True},
    {"module": "MRL3701", "subject": "Insolvency Act Updates", "content": "Review the latest amendments.", "date": "2026-02-26", "isDeadline": False},
]

# --- 3. FETCH DATA ---
def fetch_announcements(module_name=None):
    if db is None:
        # If no database key, use mock data so the app still runs
        if module_name and module_name != "Dashboard":
            return [d for d in MOCK_DATA if d["module"] == module_name]
        return MOCK_DATA

    # If database is connected, fetch real data!
    announcements = []
    try:
        if module_name and module_name != "Dashboard":
            # Fetch specific module (without DB ordering to avoid index errors)
            docs = db.collection('modules').document(module_name).collection('announcements').get()
            for doc in docs:
                announcements.append(doc.to_dict())
        else:
            # Fetch all modules manually to avoid Firebase collection_group index errors
            modules_list = ["MRL3701", "MRL3702", "PVL3701", "PVL3702", "PVL3703"]
            for mod in modules_list:
                docs = db.collection('modules').document(mod).collection('announcements').get()
                for doc in docs:
                    announcements.append(doc.to_dict())
        
        # Sort all fetched announcements by date in Python memory (newest first)
        announcements.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # If on dashboard, limit to the 20 most recent
        if not module_name or module_name == "Dashboard":
            announcements = announcements[:20]

    except Exception as e:
        st.error(f"Error fetching data: {e}")
    return announcements

# --- 4. SIDEBAR NAVIGATION ---
st.sidebar.title("⚖️ Law Portal")
st.sidebar.caption("Taswell Solomons")

st.sidebar.markdown("---")
MODULES = ["Dashboard", "MRL3701", "MRL3702", "PVL3701", "PVL3702", "PVL3703"]
selected_module = st.sidebar.radio("Navigation", MODULES)

st.sidebar.markdown("---")
st.sidebar.info("Synced automatically from Gmail via Cloud Functions.")

if db is None:
    st.sidebar.warning("⚠️ Offline Mode: Could not connect to database. Showing preview data.")

# --- 5. MAIN UI DASHBOARD ---
if selected_module == "Dashboard":
    st.title("Welcome back, Taswell.")
    st.write(f"Today is {datetime.now().strftime('%A, %d %B %Y')}")
    st.markdown("---")
    
    st.subheader("📬 Recent Announcements (All Modules)")
    emails = fetch_announcements()
    
else:
    # Individual Module View
    st.title(f"📖 {selected_module}")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    with col2:
        st.success("📝 Pinned Notes")
        st.write("- Check tutorial letters.")
        st.write("- Past papers in Google Drive.")
        
    with col1:
        st.subheader("Incoming Emails")
        emails = fetch_announcements(selected_module)

# --- 6. DISPLAY EMAILS ---
# This renders the emails beautifully in expandable boxes
if not emails:
    st.info(f"No recent announcements found for {selected_module}.")
else:
    for email in emails:
        # Check if our webhook flagged this as a deadline
        is_deadline = email.get('isDeadline', False)
        emoji = "🚨" if is_deadline else "📧"
        
        with st.expander(f"{emoji} [{email.get('module', 'N/A')}] {email.get('subject', 'No Subject')}"):
            st.caption(f"Received: {email.get('date', 'Unknown Date')}")
            if is_deadline:
                st.error("System flagged this as a potential deadline or assignment!")
            st.write(email.get('content', 'No content available.'))

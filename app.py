import streamlit as st
import time
from datetime import datetime

# Page Config
st.set_page_config(
    page_title="Africare - AI Health Assistant",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to mimic the React Design
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #0F766E;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 20px;
    }
    .stChatMessage {
        background-color: white;
        border-radius: 15px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# Mock Data (Same as React App)
LANGUAGES = {
    "en": "English",
    "ak": "Akan", 
    "sw": "Swahili",
    "ga": "Ga",
    "ew": "Ewe",
    "fa": "Fante"
}

TRANSLATIONS = {
    "en": {
        "welcome": "Hello! I'm Africare AI.",
        "subtitle": "Ask me anything about health.",
        "offline": "Offline Mode",
        "online": "Online Mode",
        "disclaimer": "This is an AI assistant. For medical emergencies, please visit the nearest hospital."
    },
    "sw": {
        "welcome": "Hujambo! Mimi ni Africare AI.",
        "subtitle": "Niulize chochote kuhusu afya.",
        "offline": "Hali ya Nje ya Mtandao",
        "online": "Mtandaoni",
        "disclaimer": "Hii ni akili bandia. Kwa dharura, tembelea hospitali."
    },
    "ak": {
        "welcome": "Akwaaba! Me ne Africare AI.",
        "subtitle": "Bisa me biribiara fa apɔwmuden ho.",
        "offline": "Offline Mode",
        "online": "Wɔ Intanɛt So",
        "disclaimer": "Sɛ woyare pa ara a, kɔ asopiti."
    }
}

KNOWLEDGE_BASE = {
    "malaria": {
        "en": "Malaria is caused by parasites transmitted by mosquitoes. Symptoms: Fever, Chills, Headache.",
        "sw": "Malaria inasababishwa na mbu. Dalili: Homa, Baridi, Kuumwa kichwa.",
        "ak": "Malaria yɛ yareɛ a mmoawa de ba. Nsɛnkyerɛnne: Huraeɛ, Awɔ, Tipae."
    },
    "cholera": {
        "en": "Cholera is caused by contaminated water. Symptoms: Severe diarrhea, Dehydration.",
        "sw": "Kipindupindu kinasababishwa na maji machafu. Dalili: Kuhara sana.",
        "ak": "Cholera fi nsuo a ɛnni."
    }
}

# Sidebar
with st.sidebar:
    st.title("🌍 Africare")
    st.caption("Health Companion")
    
    lang_code = st.selectbox("Language", options=list(LANGUAGES.keys()), format_func=lambda x: LANGUAGES[x])
    
    is_offline = st.toggle("Offline Mode", value=False)
    mode_text = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])["offline"] if is_offline else TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])["online"]
    st.caption(f"Status: {mode_text}")
    
    st.divider()
    st.subheader("Verified Sources")
    st.markdown("- DHS Program\n- WHO Africa\n- Ghana Health Service")

# Main Chat Interface
t = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])

st.title(t["welcome"])
st.write(t["subtitle"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Type your health question..."):
    # User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI Logic
    response = ""
    lower_input = prompt.lower()
    
    with st.chat_message("assistant"):
        with st.spinner("Africare is thinking..."):
            time.sleep(1) # Simulate delay
            
            if is_offline:
                if "malaria" in lower_input:
                    response = KNOWLEDGE_BASE["malaria"].get(lang_code, KNOWLEDGE_BASE["malaria"]["en"]) + "\n\n*(Offline Cache)*"
                elif "cholera" in lower_input:
                    response = KNOWLEDGE_BASE["cholera"].get(lang_code, KNOWLEDGE_BASE["cholera"]["en"]) + "\n\n*(Offline Cache)*"
                else:
                    response = "I am offline. I can only answer questions about Malaria and Cholera."
            else:
                # Online Logic Simulation
                found = False
                for key, val in KNOWLEDGE_BASE.items():
                    if key in lower_input:
                        response = val.get(lang_code, val["en"])
                        found = True
                        break
                if not found:
                    response = "Consult a doctor for specific advice. General tip: Stay hydrated and eat well."
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

st.markdown("---")
st.caption(t["disclaimer"])

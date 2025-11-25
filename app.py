import streamlit as st
import time
from datetime import datetime

# -------------------------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Africare - AI Health Assistant",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------------
# THEMES
# -------------------------------------------------------------------
LIGHT_THEME = """
    <style>
        .main {
            background-color: #f8f9fa !important;
        }
        .stChatMessage {
            background-color: #ffffff !important;
            border-radius: 15px;
            padding: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stButton>button {
            background-color: #0F766E !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 10px 20px !important;
            border: none !important;
        }
    </style>
"""

DARK_THEME = """
    <style>
        .main {
            background-color: #0d1117 !important;
            color: #e6edf3 !important;
        }
        .stChatMessage {
            background-color: #161b22 !important;
            color: #e6edf3 !important;
            border-radius: 15px;
            padding: 12px;
            box-shadow: 0 2px 4px rgba(255,255,255,0.05);
        }
        .stButton>button {
            background-color: #238636 !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 10px 20px !important;
            border: none !important;
        }
    </style>
"""

# -------------------------------------------------------------------
# MULTILANGUAGE DATA
# -------------------------------------------------------------------
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
        "input": "Type your health question...",
        "offline_limit": "I am offline. I can only answer questions about Malaria and Cholera.",
        "default_online": "Consult a doctor for specific advice. General tip: Stay hydrated and eat well.",
        "disclaimer": "This is an AI assistant. For medical emergencies, please visit the nearest hospital."
    },
    "sw": {
        "welcome": "Hujambo! Mimi ni Africare AI.",
        "subtitle": "Niulize chochote kuhusu afya.",
        "offline": "Hali ya Nje ya Mtandao",
        "online": "Mtandaoni",
        "input": "Andika swali lako kuhusu afya...",
        "offline_limit": "Niko nje ya mtandao. Naweza kujibu Malaria au Kipindupindu tu.",
        "default_online": "Kwa ushauri maalum, wasiliana na daktari. Ushauri wa jumla: Kunywa maji mengi.",
        "disclaimer": "Hii ni akili bandia. Kwa dharura, tembelea hospitali."
    },
    "ak": {
        "welcome": "Akwaaba! Me ne Africare AI.",
        "subtitle": "Bisa me biribiara fa apɔwmuden ho.",
        "offline": "Offline Mode",
        "online": "Wɔ Intanɛt So",
        "input": "Bisa wo asɛmmisa fa apɔwmuden ho...",
        "offline_limit": "Mete offline. Metumi ma mmuae fa Malaria ne Cholera nko ara.",
        "default_online": "Di nsu bebree na didi yie. Bisa dɔkotani sɛ wopɛ nkyerɛkyerɛmu pa.",
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

# -------------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------------
with st.sidebar:
    st.title("🌍 Africare")
    st.caption("Your Health Companion")

    # language
    lang = st.selectbox(
        "Language",
        options=list(LANGUAGES.keys()),
        format_func=lambda x: LANGUAGES[x],
        index=0
    )

    # offline
    offline_mode = st.toggle("Offline Mode", value=False)
    status_label = TRANSLATIONS[lang]["offline"] if offline_mode else TRANSLATIONS[lang]["online"]
    st.caption(f"Status: {status_label}")

    # theme toggle
    st.divider()
    theme = st.radio("Theme", ["Light", "Dark"], horizontal=True)

    # sources
    st.divider()
    st.subheader("Verified Sources")
    st.markdown("- DHS Program\n- WHO Africa\n- Ghana Health Service")

# -------------------------------------------------------------------
# APPLY THEME
# -------------------------------------------------------------------
if theme == "Light":
    st.markdown(LIGHT_THEME, unsafe_allow_html=True)
else:
    st.markdown(DARK_THEME, unsafe_allow_html=True)

# -------------------------------------------------------------------
# MAIN CHAT UI
# -------------------------------------------------------------------
t = TRANSLATIONS[lang]

st.title(t["welcome"])
st.write(t["subtitle"])

# Initialize messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Replay past messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User input
if prompt := st.chat_input(t["input"]):
    # store & display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # AI response
    lower = prompt.lower()
    response = ""

    with st.chat_message("assistant"):
        with st.spinner("Africare is thinking..."):
            time.sleep(1)

            if offline_mode:
                # limited answers
                if "malaria" in lower:
                    response = KNOWLEDGE_BASE["malaria"].get(lang, KNOWLEDGE_BASE["malaria"]["en"]) + "\n\n*(Offline Cache)*"
                elif "cholera" in lower:
                    response = KNOWLEDGE_BASE["cholera"].get(lang, KNOWLEDGE_BASE["cholera"]["en"]) + "\n\n*(Offline Cache)*"
                else:
                    response = t["offline_limit"]
            else:
                # online knowledge
                matched = False
                for disease, data in KNOWLEDGE_BASE.items():
                    if disease in lower:
                        response = data.get(lang, data["en"])
                        matched = True
                        break
                if not matched:
                    response = t["default_online"]

            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

st.markdown("---")
st.caption(t["disclaimer"])

"""
Africare - Streamlit AI Health Assistant
Set optional env vars: OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY
"""

import os
import time
import requests
import streamlit as st

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="Africare - AI Health Assistant",
    page_icon="africare-log.jpg",  # local file
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# SYSTEM PROMPT & DATASET
# -------------------------
SYSTEM_PROMPT = """You are a Verified Health Information Assistant for Africa.
Always respond exactly in this structure:

Based on verified health information:
[Condition Name]

Symptoms: • item • item • item

Prevention: • item • item • item

Treatment: short instructions

Source: WHO / CDC / regional source

⚠️ Note: This is general health information. For diagnosis or treatment, consult a qualified healthcare provider.
"""

DISEASE_DATASET = {
    "malaria": {
        "name": "Malaria",
        "symptoms": [
            "High fever (often above 38°C / 100.4°F)",
            "Chills and sweating",
            "Headache",
            "Nausea and vomiting",
            "Muscle pain and fatigue"
        ],
        "prevention": [
            "Sleep under insecticide-treated mosquito nets",
            "Use indoor residual spraying",
            "Take antimalarial medication as prescribed",
            "Eliminate standing water where mosquitoes breed",
            "Wear long-sleeved clothing during dawn and dusk"
        ],
        "treatment": [
            "Seek immediate medical care",
            "Artemisinin-based combination therapies (ACTs)",
            "Never self-medicate"
        ],
        "source": "WHO Global Health Observatory – African Region"
    },
    "cholera": {
        "name": "Cholera",
        "symptoms": [
            "Watery diarrhea",
            "Vomiting",
            "Severe dehydration",
            "Leg cramps"
        ],
        "prevention": [
            "Drink safe and treated water",
            "Practice good sanitation and hygiene",
            "Wash hands frequently with soap",
            "Cook food thoroughly"
        ],
        "treatment": [
            "Immediate oral rehydration (ORS)",
            "Seek urgent medical care",
            "Severe cases require intravenous fluids and antibiotics"
        ],
        "source": "WHO African Region – Cholera Factsheet"
    },
    # ... Add other diseases as before ...
}

# -------------------------
# UI Theme
# -------------------------
def apply_theme(theme):
    if theme == "Light":
        bg = "#f7fafc"
        text = "#0f172a"
        user_bubble = "#DCF8C6"
        bot_bubble = "#ffffff"
    else:
        bg = "#0b1220"
        text = "#e6eef8"
        user_bubble = "#1f2937"
        bot_bubble = "#0b1220"

    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {bg}; color: {text}; }}
        .stButton>button {{ background-color: #0F766E; color: white; border-radius: 10px; padding: 8px 16px; }}
        .chat-user {{ background: {user_bubble}; padding: 10px; border-radius: 12px; margin-bottom:4px; }}
        .chat-bot {{ background: {bot_bubble}; padding: 10px; border-radius: 12px; margin-bottom:4px; }}
        </style>
        """, unsafe_allow_html=True
    )

# -------------------------
# Internet detection
# -------------------------
def check_internet(timeout=2):
    try:
        r = requests.get("https://www.google.com", timeout=timeout)
        return r.status_code == 200
    except:
        return False

if "internet_available" not in st.session_state:
    st.session_state.internet_available = check_internet()

# -------------------------
# API Keys
# -------------------------
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# -------------------------
# LLM Wrappers
# -------------------------
def call_openai(system_prompt, user_prompt):
    if not OPENAI_KEY:
        raise RuntimeError("OpenAI key not set.")
    try:
        import openai
        openai.api_key = OPENAI_KEY
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system","content":system_prompt},{"role":"user","content":user_prompt}],
            temperature=0.1, max_tokens=512
        )
        return resp.choices[0].message.content.strip()
    except:
        return "Error calling OpenAI."

def call_groq(system_prompt, user_prompt):
    return "Groq call placeholder."

def call_gemini(system_prompt, user_prompt):
    return "Gemini call placeholder."

# -------------------------
# Utility functions
# -------------------------
def find_disease(query):
    q = query.lower()
    for key, info in DISEASE_DATASET.items():
        if key in q or info["name"].lower() in q:
            return info
    return None

def format_health(info):
    symptoms = " • ".join(info["symptoms"])
    prevention = " • ".join(info["prevention"])
    treatment = " • ".join(info["treatment"])
    text = (
        f"Based on verified health information:\n{info['name']}\n\n"
        f"Symptoms: • {symptoms}\n\n"
        f"Prevention: • {prevention}\n\n"
        f"Treatment: • {treatment}\n\n"
        f"Source: {info['source']}\n\n"
        "⚠️ Note: This is general health information. For diagnosis and treatment, consult a qualified healthcare provider."
    )
    return text

def generate_response(user_text, force_offline=False):
    dataset_info = find_disease(user_text)
    if force_offline or not st.session_state.internet_available or not any([OPENAI_KEY, GROQ_KEY, GEMINI_KEY]):
        if dataset_info:
            return format_health(dataset_info)
        return "Information not available offline. Please consult a healthcare provider."

    # Try LLM providers in order
    for fn in [call_openai, call_gemini, call_groq]:
        try:
            text = fn(SYSTEM_PROMPT, user_text)
            if dataset_info:
                return format_health(dataset_info)  # always prefer dataset template
            return text
        except:
            continue
    if dataset_info:
        return format_health(dataset_info)
    return "Unable to retrieve online info. Please consult a healthcare provider."

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.image("africare.jpg", width=140)
    st.title("Africare AI")
    st.caption("Your African Health Companion")

    theme = st.radio("Theme", ["Light","Dark"], index=0)
    apply_theme(theme)

    st.markdown("### Connection Mode")
    conn_mode = st.selectbox("Mode", ["Auto-detect","Force Online","Force Offline"])
    if conn_mode=="Force Online":
        force_offline=False
    elif conn_mode=="Force Offline":
        force_offline=True
    else:
        force_offline=not st.session_state.internet_available

    if st.button("Clear History"):
        st.session_state.messages = []

# -------------------------
# Chat display & input
# -------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Hello! I'm Africare AI")
st.write("Ask me anything about health (verified format)")

# Display previous messages
for msg in st.session_state.messages:
    role = msg.get("role","assistant")
    content = msg.get("content","")
    if role=="user":
        st.markdown(f"<div class='chat-user'><b>You:</b><br>{content}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bot'><b>Africare:</b><br>{content}</div>", unsafe_allow_html=True)

# Chat input
prompt = st.chat_input("Type your health question (e.g., 'What is malaria?')...")
if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
    response = generate_response(prompt, force_offline=force_offline)
    st.session_state.messages.append({"role":"assistant","content":response})
    st.experimental_rerun()  # optional: immediately refresh to show new messages

st.markdown("---")
st.caption("This is general health information. For diagnosis or treatment, consult a qualified healthcare provider.")

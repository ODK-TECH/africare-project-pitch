# app.py
"""
Africare - Streamlit AI Health Assistant
Place africare-log.jpg beside this file.
Set optional env vars: OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY
"""

import os
import time
import requests
import streamlit as st
from datetime import datetime

# -------------------------
# Page config (uses local image as icon)
# -------------------------
st.set_page_config(
    page_title="Africare - AI Health Assistant",
    page_icon="africare-log.jpg",  # local file
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# System Prompt (enforces the verified-health structure)
# -------------------------
SYSTEM_PROMPT = """You are a Verified Health Information Assistant for Africa.
When a user asks a health question (like "what is malaria?"), ALWAYS respond exactly in this structure and nothing else:

Based on verified health information:
[Condition Name]

Symptoms: • item • item • item

Prevention: • item • item • item

Treatment: [short instructions]

Source: [WHO / CDC / WHO regional page or similar]

⚠️ Note: This is general health information. For diagnosis or treatment, please consult a qualified healthcare provider.

RULES:
- If the disease/condition exists in the internal DISEASE_DATASET, use that dataset entry exactly (do not invent).
- If not in dataset, produce a concise WHO-style factual answer.
- Do not provide unverified claims or experimental/unapproved treatments.
- Keep the bullet format (•) exactly as shown. Keep headings identical.
"""

# -------------------------
# Disease dataset: 15 common African-region diseases
# -------------------------
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
            "Take antimalarial medication as prescribed (especially for pregnant women)",
            "Eliminate standing water where mosquitoes breed",
            "Wear long-sleeved clothing during dawn and dusk"
        ],
        "treatment": [
            "Seek immediate medical care",
            "Artemisinin-based combination therapies (ACTs) are the recommended first-line treatment",
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
    "tuberculosis": {
        "name": "Tuberculosis (TB)",
        "symptoms": [
            "Persistent cough (more than 2 weeks)",
            "Chest pain",
            "Coughing blood",
            "Weight loss",
            "Night sweats"
        ],
        "prevention": [
            "Early detection and treatment",
            "BCG vaccination for infants where recommended",
            "Good ventilation and sunlight",
            "Avoid close prolonged contact with infected individuals"
        ],
        "treatment": [
            "Seek medical evaluation",
            "Treatment typically includes a 6-month antibiotic regimen",
            "Do not stop medication early"
        ],
        "source": "WHO TB Factsheet"
    },
    "typhoid": {
        "name": "Typhoid Fever",
        "symptoms": [
            "High fever",
            "Weakness and stomach pain",
            "Constipation or diarrhea",
            "Headache"
        ],
        "prevention": [
            "Drink clean water",
            "Wash hands with soap",
            "Eat properly cooked food",
            "Get vaccinated where available"
        ],
        "treatment": [
            "Seek prompt medical treatment",
            "Antibiotics prescribed by a health professional"
        ],
        "source": "WHO Typhoid Factsheet"
    },
    "dengue": {
        "name": "Dengue Fever",
        "symptoms": [
            "High fever",
            "Severe headache",
            "Joint and muscle pain",
            "Pain behind the eyes",
            "Rash"
        ],
        "prevention": [
            "Avoid mosquito bites",
            "Use mosquito repellents",
            "Eliminate stagnant water",
            "Wear protective clothing"
        ],
        "treatment": [
            "Seek medical care",
            "Maintain hydration and supportive care",
            "Avoid aspirin and NSAIDs (use acetaminophen if needed)"
        ],
        "source": "WHO Dengue Factsheet"
    },
    "hepatitis_b": {
        "name": "Hepatitis B",
        "symptoms": [
            "Fatigue",
            "Yellowing of eyes/skin (jaundice)",
            "Dark urine",
            "Abdominal pain"
        ],
        "prevention": [
            "Get vaccinated",
            "Avoid sharing needles",
            "Ensure safe medical procedures"
        ],
        "treatment": [
            "Consult a healthcare provider",
            "Antiviral medications for chronic cases as advised by specialists"
        ],
        "source": "WHO Hepatitis B Factsheet"
    },
    "measles": {
        "name": "Measles",
        "symptoms": [
            "High fever",
            "Cough",
            "Runny nose",
            "Red watery eyes",
            "Skin rash"
        ],
        "prevention": [
            "MMR vaccination",
            "Maintain high immunization coverage"
        ],
        "treatment": [
            "Seek medical care",
            "Supportive treatment including fluids, rest, and vitamin A supplements"
        ],
        "source": "WHO Measles Overview"
    },
    "covid19": {
        "name": "COVID-19",
        "symptoms": [
            "Fever",
            "Cough",
            "Fatigue",
            "Loss of taste or smell",
            "Shortness of breath"
        ],
        "prevention": [
            "Vaccination",
            "Handwashing",
            "Wearing masks in crowded places",
            "Good ventilation"
        ],
        "treatment": [
            "Seek medical care for severe symptoms",
            "Supportive care per national guidelines",
            "Follow local public health guidance"
        ],
        "source": "WHO COVID-19 Updates"
    },
    "ebola": {
        "name": "Ebola Virus Disease",
        "symptoms": [
            "Fever",
            "Severe weakness",
            "Vomiting",
            "Diarrhea",
            "Bleeding"
        ],
        "prevention": [
            "Avoid contact with infected bodily fluids",
            "Safe burials",
            "Use personal protective equipment",
            "Avoid bushmeat"
        ],
        "treatment": [
            "Seek urgent medical care",
            "Supportive treatment in specialized centers",
            "Follow infection-control measures"
        ],
        "source": "WHO Ebola Factsheet"
    },
    "lassa_fever": {
        "name": "Lassa Fever",
        "symptoms": [
            "Fever",
            "Weakness",
            "Headache",
            "Sore throat",
            "Chest pain"
        ],
        "prevention": [
            "Avoid contact with rodents and their droppings",
            "Food storage hygiene",
            "Prompt isolation of suspicious cases"
        ],
        "treatment": [
            "Seek urgent medical care",
            "Ribavirin may be used in some cases under supervision"
        ],
        "source": "WHO Lassa Fever Factsheet"
    },
    "yellow_fever": {
        "name": "Yellow Fever",
        "symptoms": [
            "Fever",
            "Chills",
            "Severe headache",
            "Jaundice"
        ],
        "prevention": [
            "Vaccination",
            "Avoid mosquito bites",
            "Vector control"
        ],
        "treatment": [
            "Supportive care in hospital",
            "No specific antiviral therapy for general use"
        ],
        "source": "WHO Yellow Fever Factsheet"
    },
    "schistosomiasis": {
        "name": "Schistosomiasis",
        "symptoms": [
            "Rash or itchy skin",
            "Fever",
            "Cough",
            "Abdominal pain",
            "Blood in urine or stool"
        ],
        "prevention": [
            "Avoid swimming in freshwater in endemic areas",
            "Improved sanitation",
            "Safe water supplies"
        ],
        "treatment": [
            "Seek medical care",
            "Praziquantel is standard treatment"
        ],
        "source": "WHO Schistosomiasis Factsheet"
    },
    "trachoma": {
        "name": "Trachoma",
        "symptoms": [
            "Eye irritation",
            "Redness",
            "Discharge from the eye",
            "Pain in advanced cases"
        ],
        "prevention": [
            "Facial cleanliness",
            "Environmental improvements",
            "SAFE strategy (Surgery, Antibiotics, Facial cleanliness, Environmental improvement)"
        ],
        "treatment": [
            "Antibiotics for infection",
            "Surgery for advanced disease"
        ],
        "source": "WHO Trachoma Factsheet"
    },
    "onchocerciasis": {
        "name": "Onchocerciasis (River Blindness)",
        "symptoms": [
            "Severe itching",
            "Skin nodules",
            "Visual impairment and blindness in advanced cases"
        ],
        "prevention": [
            "Mass drug administration",
            "Vector control"
        ],
        "treatment": [
            "Ivermectin as part of supervised mass treatment programs"
        ],
        "source": "WHO Onchocerciasis Factsheet"
    },
    "hiv_aids": {
        "name": "HIV/AIDS",
        "symptoms": [
            "Flu-like symptoms in early stages",
            "Weight loss",
            "Recurrent infections",
            "Long-term immune suppression"
        ],
        "prevention": [
            "Use condoms during sex",
            "Screening of blood products",
            "HIV testing and counselling",
            "Needle exchange programs"
        ],
        "treatment": [
            "Antiretroviral therapy (ART) under medical supervision",
            "Regular follow-up and adherence to therapy"
        ],
        "source": "WHO HIV/AIDS Factsheet"
    }
}

# -------------------------
# UI Translations & small texts
# -------------------------
LANGUAGES = {"en": "English"}
TRANSLATIONS = {
    "en": {
        "welcome": "Hello! I'm Africare AI.",
        "subtitle": "Ask me anything about health. (Verified format)",
        "online": "Online Mode",
        "offline": "Offline Mode",
        "clear": "Clear History",
        "disclaimer": "This is general health information. For diagnosis and treatment, consult a qualified healthcare provider."
    }
}

# -------------------------
# Theme CSS
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
        body {{ background-color: {bg}; color: {text}; }}
        .stApp {{ background-color: {bg}; }}
        .stButton>button {{ background-color: #0F766E; color: white; border-radius: 10px; padding: 8px 16px; }}
        .chat-user {{ background: {user_bubble}; padding: 10px; border-radius: 12px; }}
        .chat-bot {{ background: {bot_bubble}; padding: 10px; border-radius: 12px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# -------------------------
# Internet check (cached per session)
# -------------------------
def check_internet(timeout=2):
    test_urls = ["https://www.google.com", "https://api.openai.com/v1/models"]
    for url in test_urls:
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code in (200, 401, 403):
                return True
        except Exception:
            continue
    return False

if "internet_available" not in st.session_state:
    st.session_state.internet_available = check_internet()

# -------------------------
# LLM keys from env
# -------------------------
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# -------------------------
# LLM call wrappers
# - OpenAI: tries openai package, falls back to HTTP request
# - Groq/Gemini: placeholders (HTTP examples); adapt to actual provider SDKs if available
# -------------------------
def call_openai_chat(system_prompt, user_prompt, model="gpt-4o-mini", max_tokens=512):
    if not OPENAI_KEY:
        raise RuntimeError("OpenAI key not set.")
    try:
        import openai
        openai.api_key = OPENAI_KEY
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # fallback via HTTP
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1
        }
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"].strip()

def call_groq(system_prompt, user_prompt):
    # Placeholder implementation — replace with Groq SDK/endpoint specifics when available
    if not GROQ_KEY:
        raise RuntimeError("Groq key not set.")
    url = "https://api.groq.cloud/v1/completions"  # example placeholder
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {"prompt": system_prompt + "\n\n" + user_prompt, "max_tokens": 512}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    data = r.json()
    # Try several possible fields
    return data.get("text") or data.get("output") or str(data)

def call_gemini(system_prompt, user_prompt):
    # Placeholder implementation — replace with actual Gemini/PaLM SDK usage
    if not GEMINI_KEY:
        raise RuntimeError("Gemini key not set.")
    # Example: Google's PaLM REST endpoint structure differs — adapt when you have API shape
    url = "https://generativeapi.googleapis.com/v1beta2/models/text-bison-001:generate"
    headers = {"Authorization": f"Bearer {GEMINI_KEY}", "Content-Type": "application/json"}
    payload = {"prompt": {"text": system_prompt + "\n\n" + user_prompt}, "maxOutputTokens": 512}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "candidates" in data and len(data["candidates"]) > 0:
        return data["candidates"][0].get("content", "").strip()
    return str(data)

# -------------------------
# Utility: find disease in dataset (simple matching)
# -------------------------
def find_disease_in_dataset(query):
    q = query.lower()
    for key, info in DISEASE_DATASET.items():
        if key in q or info["name"].lower() in q:
            return info
    return None

# -------------------------
# Formatter: produce the exact template text for a disease info dict
# -------------------------
def format_verified_health(info):
    # Format lists into bullet strings separated by " • "
    symptoms = " • ".join(info["symptoms"])
    prevention = " • ".join(info["prevention"])
    treatment = " • ".join(info["treatment"])
    text = (
        "Based on verified health information:\n"
        f"{info['name']}\n\n"
        f"Symptoms: • {symptoms}\n\n"
        f"Prevention: • {prevention}\n\n"
        f"Treatment: {' '.join(info['treatment']) if isinstance(info['treatment'], list) and len(info['treatment'])==1 else ' • '.join(info['treatment'])}\n\n"
        f"Source: {info.get('source','WHO')}\n\n"
        "⚠️ Note: This is general health information. For diagnosis and treatment, please consult a qualified healthcare provider."
    )
    return text

# -------------------------
# Main responder (tries providers in order, falls back to dataset)
# -------------------------
def generate_response(user_query, providers_order, force_offline=False, lang="en"):
    # First check dataset match
    dataset_info = find_disease_in_dataset(user_query)
    # If forced offline or no provider keys, or internet not available => offline behavior
    internet_ok = st.session_state.internet_available
    if force_offline or not internet_ok or not (OPENAI_KEY or GROQ_KEY or GEMINI_KEY):
        if dataset_info:
            return format_verified_health(dataset_info)  # exact dataset usage
        else:
            # If not in dataset and offline, return safe generic instruction
            return (
                "Based on verified health information:\n"
                f"{user_query.strip().capitalize()}\n\n"
                "Symptoms: • Information not available in offline dataset.\n\n"
                "Prevention: • Information not available in offline dataset.\n\n"
                "Treatment: Please consult a qualified healthcare provider.\n\n"
                "Source: Local offline dataset (no online sources available)\n\n"
                "⚠️ Note: This is general health information. For diagnosis and treatment, please consult a qualified healthcare provider."
            )

    # Online path: try providers in order
    last_error = None
    for p in providers_order:
        p = p.lower()
        try:
            if p == "openai" and OPENAI_KEY:
                text = call_openai_chat(SYSTEM_PROMPT, user_query)
                # If dataset exists, prefer dataset-formatted text — but the system prompt instructs model to follow template
                if dataset_info:
                    # to be safe, enforce dataset content: return dataset format
                    return format_verified_health(dataset_info)
                return text
            if p == "groq" and GROQ_KEY:
                text = call_groq(SYSTEM_PROMPT, user_query)
                if dataset_info:
                    return format_verified_health(dataset_info)
                return text
            if p == "gemini" and GEMINI_KEY:
                text = call_gemini(SYSTEM_PROMPT, user_query)
                if dataset_info:
                    return format_verified_health(dataset_info)
                return text
        except Exception as e:
            last_error = str(e)
            # try next provider
            continue

    # If no provider succeeded, fallback to dataset or generic
    if dataset_info:
        return format_verified_health(dataset_info)
    # fallback generic
    return (
        "Based on verified health information:\n"
        f"{user_query.strip().capitalize()}\n\n"
        "Symptoms: • Information not available in offline dataset.\n\n"
        "Prevention: • Information not available in offline dataset.\n\n"
        "Treatment: Please consult a qualified healthcare provider.\n\n"
        "Source: No online provider available\n\n"
        "⚠️ Note: This is general health information. For diagnosis and treatment, please consult a qualified healthcare provider."
    )

# -------------------------
# Streamlit UI: Sidebar
# -------------------------
with st.sidebar:
    st.image("africare.jpg", width=140)
    st.title("Africare AI")
    st.caption("Your African Health Companion")

    lang = st.selectbox("Language", options=list(LANGUAGES.keys()), format_func=lambda x: LANGUAGES[x])

    theme = st.radio("Theme", ["Light", "Dark"], index=0)
    apply_theme(theme)

    st.markdown("### Connection")
    if st.session_state.internet_available:
        st.success("Internet: Available")
    else:
        st.warning("Internet: Not detected")

    conn_mode = st.selectbox("Connection Mode", ["Auto-detect", "Force Online", "Force Offline"])
    if conn_mode == "Force Online":
        force_offline = False
    elif conn_mode == "Force Offline":
        force_offline = True
    else:
        # Auto-detect: offline if internet not available
        force_offline = False if st.session_state.internet_available else True

    st.divider()
    st.subheader("LLM Providers (optional keys)")
    st.markdown("Set API keys as environment variables: `OPENAI_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`.")
    provider_order = st.multiselect(
        "Provider order (tried top → bottom)",
        options=["openai", "gemini", "groq"],
        default=["openai", "gemini", "groq"]
    )
    if not provider_order:
        provider_order = ["openai", "gemini", "groq"]

    st.divider()
    if st.button(TRANSLATIONS["en"]["clear"]):
        st.session_state.messages = []
        st.success("History cleared!")

    st.divider()
    st.subheader("Verified Sources")
    st.markdown("- WHO Africa\n- Ghana Health Service\n- CDC Africa\n- UNICEF")

# -------------------------
# Main area
# -------------------------
t = TRANSLATIONS["en"]
st.title(t["welcome"])
st.write(t["subtitle"])

if "messages" not in st.session_state:
    st.session_state.messages = []

# display chat
for msg in st.session_state.messages:
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    if role == "user":
        st.markdown(f"<div class='chat-user'><b>You:</b><br/>{content}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bot'><b>Africare:</b><br/>{content}</div>", unsafe_allow_html=True)

# Chat input
prompt = st.chat_input("Type your health question (e.g., 'What is malaria?')...")
if prompt:
    # Save user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.experimental_rerun()  # cause UI to show user msg immediately (we'll handle response next rerun)

# On rerun: if last message is user and has no assistant reply, generate it
def last_msg_needs_reply():
    msgs = st.session_state.messages
    if not msgs:
        return False
    # If last is user or last assistant was before user, reply
    last = msgs[-1]
    if last["role"] == "user":
        # check if there's an assistant next — not
        return True
    return False

if last_msg_needs_reply():
    user_text = st.session_state.messages[-1]["content"]
    with st.spinner("Africare is thinking..."):
        # generate
        response_text = generate_response(user_text, providers_order=provider_order, force_offline=force_offline, lang=lang)
        time.sleep(0.6)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.experimental_rerun()

# footer
st.markdown("---")
st.caption(t["disclaimer"])

# app.py
"""
Africare - AI Health Assistant (Streamlit)
Single-file app for GitHub: copy-paste into `app.py`.
Place `africare-log.jpg` in the same repository root.

Features:
- Dual Light/Dark theme
- Expanded offline knowledge base (12+ diseases)
- System prompt that enforces verified-health response format
- Integrated optional LLM providers (OpenAI / Groq / Gemini) - uses env vars if present
- Online/offline auto-detection + manual override
- Clear History button
- Fallback deterministic offline responder that returns the specified template
Notes:
- Groq/Gemini blocks are placeholders. Adapt endpoints if/when you have provider docs.
- Do NOT commit API keys to repo. Use environment variables:
    OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY
"""

import os
import time
import json
import requests
import streamlit as st
from typing import Optional

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="Africare - AI Health Assistant",
    page_icon="africare-log.jpg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# Theme/CSS
# -------------------------
def apply_theme(theme: str):
    if theme == "Light":
        bg = "#f8f9fa"
        text = "#0f172a"
        bubble_user = "#DCF8C6"
        bubble_bot = "#FFFFFF"
    else:
        bg = "#0b1220"
        text = "#e6eef5"
        bubble_user = "#1f2a37"
        bubble_bot = "#15202b"

    st.markdown(
        f"""
    <style>
    body {{ background-color: {bg}; color: {text}; }}
    .main {{ background-color: {bg}; }}
    .stButton>button {{ background-color: #0F766E; color: white; border-radius: 10px; padding: 8px 16px; border: none; }}
    .stChatMessage {{ border-radius: 12px; padding: 10px; margin-bottom: 8px; }}
    /* role-specific (visual hint) */
    div[data-testid="stVerticalBlock"] > .stChatMessage[data-role="user"] {{
        background: {bubble_user};
    }}
    div[data-testid="stVerticalBlock"] > .stChatMessage[data-role="assistant"] {{
        background: {bubble_bot};
    }}
    .small-muted {{ font-size:0.85rem; color: #9aa4b2; }}
    </style>
    """,
        unsafe_allow_html=True,
    )

# -------------------------
# Translations (minimal)
# -------------------------
LANGUAGES = {
    "en": "English",
    "ak": "Akan",
    "sw": "Swahili",
    "ga": "Ga",
    "ew": "Ewe",
    "fa": "Fante",
}

TRANSLATIONS = {
    "en": {
        "welcome": "Hello! I'm Africare AI.",
        "subtitle": "Ask me anything about health.",
        "offline": "Offline Mode",
        "online": "Online Mode",
        "disclaimer": "This is general health information. For diagnosis or treatment, consult a qualified healthcare provider.",
        "clear": "Clear History",
    },
    # Additional language keys exist but English is default for this single-file app
}

# -------------------------
# Verified response system prompt (enforce format)
# -------------------------
SYSTEM_PROMPT = """
You are Africare — a Verified Health Information Assistant for Africa.
WHENEVER the user asks about a disease, condition, symptom, prevention, or treatment, ALWAYS respond in this EXACT structure and tone:

Based on verified health information:
[Condition Name]

Symptoms: • Item 1 • Item 2 • Item 3

Prevention: • Item 1 • Item 2 • Item 3

Treatment: Short guidance. When to seek care. First-line treatments if applicable.

Source: <authoritative source — WHO / CDC / Africa CDC / country ministry>

⚠️ Note: This is general health information. For diagnosis and treatment, please consult a qualified healthcare provider.

RULES:
- Use the DISEASE_DATASET if it contains the condition. If present, use the dataset's Source exactly.
- Keep language factual, concise, and avoid clinical speculation.
- Do not provide prescriptions or medication dosages beyond named recommended first-line therapies.
- If the condition is not known, provide a short WHO-style summary and include "Source: WHO" or "Source: WHO / CDC" as appropriate.
- Always include the "Based on verified health information:" prefix and the final warning note exactly as above.
"""

# -------------------------
# Knowledge dataset (12+ diseases) - offline fallback
# -------------------------
DISEASE_DATASET = {
    "malaria": {
        "name": "Malaria",
        "symptoms": [
            "High fever (often above 38°C / 100.4°F)",
            "Chills and sweating",
            "Headache",
            "Nausea and vomiting",
            "Muscle pain and fatigue",
        ],
        "prevention": [
            "Sleep under insecticide-treated mosquito nets",
            "Use indoor residual spraying",
            "Take antimalarial medication as prescribed (especially for pregnant women)",
            "Eliminate standing water where mosquitoes breed",
            "Wear long-sleeved clothing during dawn and dusk",
        ],
        "treatment": [
            "Seek immediate medical care",
            "Artemisinin-based combination therapies (ACTs) are first-line",
            "Never self-medicate",
        ],
        "source": "WHO Global Health Observatory – African Region",
    },
    "cholera": {
        "name": "Cholera",
        "symptoms": [
            "Watery diarrhea",
            "Vomiting",
            "Severe dehydration",
            "Leg cramps",
        ],
        "prevention": [
            "Drink safe and treated water",
            "Practice good sanitation and hygiene",
            "Wash hands with soap frequently",
            "Cook food thoroughly",
        ],
        "treatment": [
            "Immediate oral rehydration",
            "Seek urgent medical care",
            "Severe cases require intravenous fluids and antibiotics",
        ],
        "source": "WHO African Region – Cholera Factsheet",
    },
    "tuberculosis": {
        "name": "Tuberculosis (TB)",
        "symptoms": [
            "Persistent cough (more than 2 weeks)",
            "Chest pain",
            "Coughing blood",
            "Weight loss",
            "Night sweats",
        ],
        "prevention": [
            "Early detection and treatment",
            "BCG vaccination (where indicated)",
            "Good ventilation and sunlight in living spaces",
            "Avoid close prolonged contact with infected individuals",
        ],
        "treatment": [
            "Seek medical evaluation",
            "Standard 6-month antibiotic regimen under supervision",
            "Do not discontinue medication early",
        ],
        "source": "WHO TB Factsheet",
    },
    "typhoid": {
        "name": "Typhoid Fever",
        "symptoms": [
            "High fever",
            "Weakness and stomach pain",
            "Constipation or diarrhea",
            "Headache",
        ],
        "prevention": [
            "Drink clean water",
            "Wash hands with soap",
            "Eat cooked food",
            "Get vaccinated when available",
        ],
        "treatment": [
            "Seek prompt medical treatment",
            "Antibiotics prescribed by a health professional",
        ],
        "source": "WHO Typhoid Factsheet",
    },
    "dengue": {
        "name": "Dengue Fever",
        "symptoms": [
            "High fever",
            "Severe headache",
            "Joint and muscle pain",
            "Pain behind the eyes",
            "Rash",
        ],
        "prevention": [
            "Avoid mosquito bites",
            "Use mosquito repellents",
            "Eliminate stagnant water",
            "Wear protective clothing",
        ],
        "treatment": [
            "Seek medical care for warning signs",
            "Drink plenty of fluids",
            "Avoid aspirin or ibuprofen unless advised by a clinician",
        ],
        "source": "WHO Dengue Factsheet",
    },
    "hepatitis_b": {
        "name": "Hepatitis B",
        "symptoms": [
            "Fatigue",
            "Yellowing of eyes/skin (jaundice)",
            "Dark urine",
            "Abdominal pain",
        ],
        "prevention": [
            "Get vaccinated",
            "Avoid sharing needles",
            "Ensure safe medical procedures and blood screening",
        ],
        "treatment": [
            "Consult a healthcare provider",
            "Antiviral medications for chronic cases when indicated",
        ],
        "source": "WHO Hepatitis B Factsheet",
    },
    "measles": {
        "name": "Measles",
        "symptoms": [
            "High fever",
            "Cough",
            "Runny nose",
            "Red watery eyes",
            "Skin rash",
        ],
        "prevention": [
            "MMR / measles vaccination",
            "Good immunization coverage",
        ],
        "treatment": [
            "Seek medical care when severe",
            "Supportive treatment including fluids and rest",
            "Vitamin A supplements as advised",
        ],
        "source": "WHO Measles Overview",
    },
    "covid19": {
        "name": "COVID-19",
        "symptoms": [
            "Fever",
            "Cough",
            "Fatigue",
            "Loss of taste or smell",
            "Shortness of breath",
        ],
        "prevention": [
            "Vaccination",
            "Handwashing",
            "Wearing masks in crowded places as recommended",
            "Good ventilation",
        ],
        "treatment": [
            "Seek medical care when breathless or at high risk",
            "Supportive care per national guidelines",
        ],
        "source": "WHO COVID-19 Updates",
    },
    "ebola": {
        "name": "Ebola Virus Disease",
        "symptoms": [
            "Fever",
            "Severe weakness",
            "Vomiting",
            "Diarrhea",
            "Bleeding (in some cases)",
        ],
        "prevention": [
            "Avoid contact with infected bodily fluids",
            "Safe burials and infection control",
            "Use personal protective equipment (PPE) for caregivers",
            "Avoid bushmeat",
        ],
        "treatment": [
            "Seek urgent specialized medical care",
            "Supportive treatment in isolation and specialized centers",
        ],
        "source": "WHO Ebola Factsheet",
    },
    "hiv": {
        "name": "HIV/AIDS",
        "symptoms": [
            "Early: flu-like illness",
            "Long-term: weight loss, recurrent infections, chronic fatigue",
        ],
        "prevention": [
            "Use condoms and safe sex practices",
            "Needle-exchange programs",
            "Test and treat strategy (ART for positives)",
        ],
        "treatment": [
            "Antiretroviral therapy (ART)",
            "Regular medical follow-up",
        ],
        "source": "WHO HIV/AIDS Factsheet",
    },
    "schistosomiasis": {
        "name": "Schistosomiasis (Bilharzia)",
        "symptoms": [
            "Abdominal pain",
            "Blood in urine or stools",
            "Diarrhea",
            "Fatigue",
        ],
        "prevention": [
            "Avoid contact with contaminated fresh water",
            "Improve sanitation",
            "Mass drug administration where recommended",
        ],
        "treatment": [
            "Praziquantel administered under guidance",
            "Seek local public health advice",
        ],
        "source": "WHO Schistosomiasis Factsheet",
    },
    "lassa_fever": {
        "name": "Lassa Fever",
        "symptoms": [
            "Fever",
            "Weakness",
            "Headache",
            "Sore throat",
            "In severe cases: bleeding",
        ],
        "prevention": [
            "Avoid contact with rodent excreta",
            "Practice food hygiene and rodent control",
        ],
        "treatment": [
            "Seek urgent medical care",
            "Ribavirin may be used in some cases (clinical guidance required)",
        ],
        "source": "WHO Lassa Fever Factsheet",
    },
}

# -------------------------
# Helper: format disease into required template
# -------------------------
def format_verified_response(info: dict) -> str:
    """
    Output the exact format requested by user, beginning with:
    'Based on verified health information:'
    and including sections inline with '•' bullets.
    """
    def join_bullets(items):
        # join items into "• item • item • item"
        if not items:
            return ""
        return " • ".join(items)

    symptoms = join_bullets(info.get("symptoms", []))
    prevention = join_bullets(info.get("prevention", []))
    treatment = join_bullets(info.get("treatment", []))
    source = info.get("source", "WHO")

    text = (
        "Based on verified health information:\n\n"
        f"{info.get('name', '')}\n\n"
        f"Symptoms: • {symptoms}\n\n"
        f"Prevention: • {prevention}\n\n"
        f"Treatment: {treatment}\n\n"
        f"Source: {source}\n\n"
        "⚠️ Note: This is general health information. For diagnosis and treatment, please consult a qualified healthcare provider."
    )
    return text

# -------------------------
# Quick internet probe (cached once per session)
# -------------------------
def check_internet(timeout: float = 2.0) -> bool:
    test_urls = ["https://api.openai.com/v1/models", "https://www.google.com"]
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
# LLM Provider keys from env (do not store secrets here)
# -------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# -------------------------
# LLM adapters (OpenAI primary; Groq & Gemini placeholders)
# -------------------------
def llm_call_openai(system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini") -> str:
    """
    Attempt to call OpenAI using openai package if available; otherwise HTTP.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not configured.")
    try:
        # try official package
        import openai
        openai.api_key = OPENAI_API_KEY
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=700,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # fallback HTTP (simple)
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "max_tokens": 700,
            "temperature": 0.2,
        }
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        d = r.json()
        return d["choices"][0]["message"]["content"].strip()

def llm_call_groq(system_prompt: str, user_prompt: str) -> str:
    """
    Placeholder Groq adapter. Adapt when you have exact API spec.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("Groq API key not configured.")
    # Placeholder: simulate call failure unless you implement the real endpoint
    raise RuntimeError("Groq adapter is a placeholder. Implement Groq API call per their docs.")

def llm_call_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Placeholder Gemini adapter. Adapt to Google PaLM/Gemini API as required.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key not configured.")
    # Placeholder: simulate call failure unless you implement the real endpoint
    raise RuntimeError("Gemini adapter is a placeholder. Implement Gemini API call per their docs.")

def generate_with_providers(system_prompt: str, user_prompt: str, providers_order: list) -> str:
    """
    Try providers in order. If none available or calls fail, raise Exception to allow fallback.
    """
    last_error = {}
    for p in providers_order:
        try:
            if p == "openai" and OPENAI_API_KEY:
                return llm_call_openai(system_prompt, user_prompt)
            if p == "groq" and GROQ_API_KEY:
                return llm_call_groq(system_prompt, user_prompt)
            if p == "gemini" and GEMINI_API_KEY:
                return llm_call_gemini(system_prompt, user_prompt)
        except Exception as e:
            last_error[p] = str(e)
            continue
    raise RuntimeError(f"No LLM provider succeeded. Errors: {json.dumps(last_error)}")

# -------------------------
# Utility: try to find disease key in user query
# -------------------------
def find_disease_in_query(query: str) -> Optional[str]:
    q = query.lower()
    # Exact key names
    for key, info in DISEASE_DATASET.items():
        if key in q or info["name"].lower() in q:
            return key
    # simple token matching (words)
    tokens = q.split()
    for key, info in DISEASE_DATASET.items():
        for tok in tokens:
            if tok and tok in key:
                return key
    return None

# -------------------------
# Sidebar UI
# -------------------------
with st.sidebar:
    st.image("africare-log.jpg", width=130)
    st.title("Africare AI")
    st.caption("Your African Health Companion")
    lang_code = st.selectbox("Language", options=list(LANGUAGES.keys()), format_func=lambda x: LANGUAGES[x])
    theme = st.radio("Theme", ["Light", "Dark"], index=0)
    apply_theme(theme)

    # Connection indicator + override
    st.markdown("### Connection")
    if st.session_state.internet_available:
        st.success("Internet: Available")
    else:
        st.warning("Internet: Not detected")

    conn_override = st.selectbox("Connection Mode", options=["Auto-detect", "Force Online", "Force Offline"])
    if conn_override == "Force Online":
        is_offline = False
    elif conn_override == "Force Offline":
        is_offline = True
    else:
        is_offline = not st.session_state.internet_available

    st.divider()
    st.subheader("LLM Providers (optional)")
    st.markdown("Set your API keys as env vars: `OPENAI_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`")
    provider_order = st.multiselect(
        "Providers order (tried top → bottom)", ["openai", "gemini", "groq"], default=["openai", "gemini", "groq"]
    )

    st.divider()
    if st.button(TRANSLATIONS["en"]["clear"]):
        st.session_state.messages = []
        st.success("History cleared!")

    st.subheader("Verified Sources")
    st.markdown("- WHO Africa\n- Ghana Health Service\n- CDC Africa\n- UNICEF")

# -------------------------
# Main chat UI
# -------------------------
t = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])
st.title(t["welcome"])
st.write(t["subtitle"])

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Type your health question..."):
    # Save user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant processing
    with st.chat_message("assistant"):
        with st.spinner("Africare is thinking..."):
            time.sleep(0.6)

            # Priority: if the user explicitly asks for a disease that exists in dataset -> return formatted dataset answer
            disease_key = find_disease_in_query(prompt)

            # If offline forced OR (auto and no internet) -> use dataset fallback
            if is_offline:
                if disease_key:
                    response = format_verified_response(DISEASE_DATASET[disease_key])
                else:
                    # Generic offline guidance
                    response = (
                        "Based on verified health information:\n\n"
                        "General Health Guidance\n\n"
                        "Symptoms: • Varies by condition — monitor fever, severe pain, breathing difficulty\n\n"
                        "Prevention: • Maintain hygiene • Safe water • Vaccination where available • Avoid vectors\n\n"
                        "Treatment: Seek medical care. Local clinics and district hospitals can help with diagnosis and treatment.\n\n"
                        "Source: WHO / Local health authorities\n\n"
                        "⚠️ Note: This is general health information. For diagnosis and treatment, please consult a qualified healthcare provider."
                    )
            else:
                # Online: attempt provider(s) if keys and provider order exist; otherwise, if disease in dataset use dataset
                try:
                    if disease_key and not any([OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY]):
                        # No keys at all -> use dataset
                        response = format_verified_response(DISEASE_DATASET[disease_key])
                    else:
                        # Build LLM user prompt that asks for the verified structured output and prefers dataset info if available
                        user_prompt = (
                            "User question:\n\n"
                            f"{prompt}\n\n"
                            "If this is about a known disease and you have authoritative data (WHO/CDC), respond using the exact format:\n\n"
                            "Based on verified health information:\n\n"
                            "[Condition Name]\n\n"
                            "Symptoms: • item • item\n\n"
                            "Prevention: • item • item\n\n"
                            "Treatment: text\n\n"
                            "Source: authoritative source\n\n"
                            "⚠️ Note: This is general health information. For diagnosis and treatment, please consult a qualified healthcare provider.\n\n"
                            "If you can, prefer the local dataset facts. If the condition is not in the dataset, produce a concise WHO-style answer."
                        )
                        # Choose provider order from sidebar, with sensible default
                        order = provider_order or ["openai", "gemini", "groq"]
                        try:
                            llm_text = generate_with_providers(SYSTEM_PROMPT, user_prompt, order)
                            # Basic sanity: if LLM returned something short or appears irrelevant, fallback to dataset if possible
                            if llm_text and len(llm_text) > 30:
                                response = llm_text
                            elif disease_key:
                                response = format_verified_response(DISEASE_DATASET[disease_key])
                            else:
                                response = (
                                    "Based on verified health information:\n\n"
                                    "General Health Guidance\n\n"
                                    "Symptoms: • Varies by condition — monitor fever, severe pain, breathing difficulty\n\n"
                                    "Prevention: • Maintain hygiene • Safe water • Vaccination where available • Avoid vectors\n\n"
                                    "Treatment: Seek medical care. Local clinics and district hospitals can help with diagnosis and treatment.\n\n"
                                    "Source: WHO / Local health authorities\n\n"
                                    "⚠️ Note: This is general health information. For diagnosis and treatment, please consult a qualified healthcare provider."
                                )
                        except Exception as e:
                            # LLM failed -> fallback to dataset or generic
                            if disease_key:
                                response = format_verified_response(DISEASE_DATASET[disease_key])
                            else:
                                response = (
                                    "Based on verified health information:\n\n"
                                    "General Health Guidance\n\n"
                                    "Symptoms: • Varies by condition — monitor fever, severe pain, breathing difficulty\n\n"
                                    "Prevention: • Maintain hygiene • Safe water • Vaccination where available • Avoid vectors\n\n"
                                    "Treatment: Seek medical care. Local clinics and district hospitals can help with diagnosis and treatment.\n\n"
                                    "Source: WHO / Local health authorities\n\n"
                                    "⚠️ Note: This is general health information. For diagnosis and treatment, please consult a qualified healthcare provider."
                                )

            # Append and display assistant message
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# Footer
st.markdown("---")
st.caption(TRANSLATIONS["en"]["disclaimer"])

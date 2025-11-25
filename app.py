# africare_streamlit_llm.py
import os
import time
import json
from datetime import datetime
import requests
import streamlit as st

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    page_title="Africare - AI Health Assistant",
    page_icon="africare-log.jpg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# Helper: Theme CSS
# ---------------------------
def apply_theme(theme):
    if theme == "Light":
        bg = "#f8f9fa"
        text = "#000000"
        bubble_user = "#DCF8C6"
        bubble_bot = "#FFFFFF"
    else:
        bg = "#0f172a"
        text = "#ffffff"
        bubble_user = "#1e293b"
        bubble_bot = "#334155"

    st.markdown(f"""
    <style>
    body {{ background-color: {bg}; color: {text}; }}
    .main {{ background-color: {bg}; }}
    .stChatMessage {{ border-radius: 12px; padding: 10px; margin-bottom: 10px; }}
    .stChatMessage[data-role='user'] {{ background-color: {bubble_user}; }}
    .stChatMessage[data-role='assistant'] {{ background-color: {bubble_bot}; }}
    .stButton>button {{ background-color: #0F766E; color: white; border-radius: 10px; border: none; padding: 9px 18px; }}
    </style>
    """, unsafe_allow_html=True)

# ---------------------------
# Languages & Translations
# ---------------------------
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
        "disclaimer": "This is an AI assistant. For emergencies, contact a hospital immediately.",
        "clear": "Clear History"
    },
    "sw": {
        "welcome": "Hujambo! Mimi ni Africare AI.",
        "subtitle": "Niulize chochote kuhusu afya.",
        "offline": "Hali ya Nje ya Mtandao",
        "online": "Mtandaoni",
        "disclaimer": "Hii ni AI. Kwa dharura, tembelea hospitali.",
        "clear": "Futa Mawasiliano"
    },
    "ak": {
        "welcome": "Akwaaba! Me ne Africare AI.",
        "subtitle": "Bisa me biribiara fa apɔwmuden ho.",
        "offline": "Offline Mode",
        "online": "Wɔ Intanɛt So",
        "disclaimer": "Sɛ woyare pa ara a, kɔ asɔpiti.",
        "clear": "Pepa Abesua"
    }
}

# ---------------------------
# Knowledge base (expanded)
# ---------------------------
KNOWLEDGE_BASE = {
    "malaria": {
        "en": "Malaria is caused by mosquito-borne parasites. Symptoms include fever, chills, vomiting, and headaches.",
        "sw": "Malaria inasababishwa na mbu. Dalili ni homa, baridi, na maumivu ya kichwa.",
        "ak": "Malaria yɛ yareɛ a mmoawa de ba. Nsɛnkyerɛnne ne huraeɛ ne awɔ."
    },
    "cholera": {
        "en": "Cholera spreads through contaminated water. It causes severe diarrhea and dehydration.",
        "sw": "Kipindupindu husababishwa na maji machafu. Dalili ni kuharisha sana.",
        "ak": "Cholera fi nsuo a ɛnni hɔ te sɛɛ. Ema onipa twitwaa nsu."
    },
    "typhoid": {
        "en": "Typhoid is caused by Salmonella bacteria. Symptoms: fever, weakness, stomach pain.",
        "sw": "Typhoid inasababishwa na bakteria. Dalili ni homa, uchovu, maumivu ya tumbo.",
        "ak": "Typhoid yɛ bacteria yareɛ. Nsɛnkyerɛnne: huraeɛ, ahohuru, yaw wɔ yafunu mu."
    },
    "diabetes": {
        "en": "Diabetes affects how your body uses sugar. Symptoms include thirst, frequent urination, and fatigue.",
        "sw": "Kisukari huathiri matumizi ya sukari. Dalili: kiu, kukojoa mara nyingi.",
        "ak": "Diabetes yɛ mogya sukuru nsesae. Nsɛnkyerɛnne ne sare ogya ne da ho dwo."
    },
    "pregnancy": {
        "en": "Healthy pregnancy requires good nutrition and regular checkups.",
        "sw": "Mimba yenye afya inahitaji lishe bora na uchunguzi wa mara kwa mara.",
        "ak": "Mpa mu ho hia aduane pa ne asɛmpa mfitiase."
    }
}

# ---------------------------
# LLM Provider config (env vars)
# ---------------------------
# Provide your keys in environment variables:
# OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# ---------------------------
# Auto-detect online/offline
# ---------------------------
def check_internet(timeout=2):
    """Quick connectivity probe. Returns True if internet seems available."""
    test_urls = [
        "https://api.openai.com/v1/models",  # OpenAI endpoint
        "https://www.google.com",
    ]
    for url in test_urls:
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code in (200, 401, 403):  # 401/403 could mean reachable but auth required
                return True
        except Exception:
            continue
    return False

# Cache detection in session_state to avoid repeated probes
if "internet_available" not in st.session_state:
    st.session_state.internet_available = check_internet()

# ---------------------------
# LLM Adapter (tries providers in order)
# ---------------------------
def llm_call_openai(prompt, model="gpt-3.5-turbo"):
    if not OPENAI_KEY:
        raise RuntimeError("OpenAI API key not set.")
    try:
        # Prefer using the official openai package if installed
        import openai
        openai.api_key = OPENAI_KEY
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.2
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # Fallback to HTTP call
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.2
        }
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

def llm_call_groq(prompt):
    if not GROQ_KEY:
        raise RuntimeError("Groq API key not set.")
    # NOTE: this block is a placeholder — adapt endpoints per Groq docs when you have an account
    url = "https://api.groq.cloud/v1"  # placeholder
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "max_tokens": 512}
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    # This parsing assumes Groq returns { "text": "..." } — adjust to actual response shape
    data = r.json()
    return data.get("text") or data.get("output") or json.dumps(data)

def llm_call_gemini(prompt):
    if not GEMINI_KEY:
        raise RuntimeError("Gemini API key not set.")
    # NOTE: this block is a placeholder — adapt to Google Gemini/PaLM API when available
    url = "https://generativeapi.googleapis.com/v1beta2/models/text-bison-001:generate"  # example PaLM endpoint
    headers = {"Authorization": f"Bearer {GEMINI_KEY}", "Content-Type": "application/json"}
    payload = {"prompt": {"text": prompt}, "maxOutputTokens": 512}
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    # Try to extract text
    if "candidates" in data and len(data["candidates"])>0:
        return data["candidates"][0].get("content","").strip()
    return json.dumps(data)

def generate_with_providers(prompt, providers_order):
    """
    Attempt providers in order. If all fail or no keys present, fall back to local KB responder.
    providers_order: list of strings e.g. ["openai","groq","gemini"]
    """
    errors = {}
    for p in providers_order:
        try:
            if p == "openai" and OPENAI_KEY:
                return llm_call_openai(prompt)
            if p == "groq" and GROQ_KEY:
                return llm_call_groq(prompt)
            if p == "gemini" and GEMINI_KEY:
                return llm_call_gemini(prompt)
        except Exception as e:
            errors[p] = str(e)
            continue
    # fallback: KB + template
    return fallback_kb_response(prompt)

# ---------------------------
# Fallback KB response (deterministic)
# ---------------------------
def fallback_kb_response(prompt, lang="en"):
    """
    If no LLM provider is available or offline, we return the best match
    from the knowledge base + polite coaching message.
    """
    q = prompt.lower()
    for k, contents in KNOWLEDGE_BASE.items():
        if k in q:
            kb_text = contents.get(lang, contents.get("en"))
            return kb_text + "\n\n*(Response from local knowledge base — limited scope)*"
    # No KB match: return helpful generic advice
    return ("I couldn't find a specific entry in the offline knowledge base. "
            "General advice: stay hydrated, rest, monitor symptoms, and seek in-person care if symptoms worsen.")

# ---------------------------
# Sidebar
# ---------------------------
with st.sidebar:
    st.image("africare.jpg", width=130)
    st.title("Africare AI")
    st.caption("Your African Health Companion")

    lang_code = st.selectbox("Language", options=list(LANGUAGES.keys()), format_func=lambda x: LANGUAGES[x])

    theme = st.radio("Theme", ["Light", "Dark"])
    apply_theme(theme)

    # Display (and allow) automatic online/offline detection override
    st.markdown("### Connection")
    if st.session_state.internet_available:
        st.success("Internet: Available")
    else:
        st.warning("Internet: Not detected")

    # Allow manual override
    conn_override = st.selectbox("Connection Mode", options=["Auto-detect", "Force Online", "Force Offline"])
    if conn_override == "Force Online":
        is_offline = False
    elif conn_override == "Force Offline":
        is_offline = True
    else:
        is_offline = not st.session_state.internet_available

    st.divider()

    st.subheader("LLM Providers (optional keys)")
    st.markdown("Set API keys as environment variables: `OPENAI_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`.")
    # Provider order preference
    provider_order = st.multiselect("Provider order (tried top→bottom)", ["openai", "groq", "gemini"], default=["openai","gemini","groq"])

    st.divider()
    if st.button(TRANSLATIONS[lang_code]["clear"]):
        st.session_state.messages = []
        st.success("History cleared!")

    st.subheader("Verified Sources")
    st.markdown("- WHO Africa\n- Ghana Health Service\n- CDC Africa\n- UNICEF")

# ---------------------------
# Main UI
# ---------------------------
t = TRANSLATIONS[lang_code]
st.title(t["welcome"])
st.write(t["subtitle"])

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input and handling
if prompt := st.chat_input("Type your health question..."):
    # Save user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Decide response path
    with st.chat_message("assistant"):
        with st.spinner("Africare is thinking..."):
            time.sleep(0.6)

            # If offline (either forced or auto), use fallback kb
            if is_offline:
                response = fallback_kb_response(prompt, lang=lang_code)
            else:
                # Try providers in order; if none succeed, fallback to KB
                # If user didn't pick any provider in UI, default to trying OpenAI->Gemini->Groq
                order = provider_order or ["openai", "gemini", "groq"]
                response = generate_with_providers(prompt, order)

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# footer
st.markdown("---")
st.caption(t["disclaimer"])

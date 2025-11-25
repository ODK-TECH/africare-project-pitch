import streamlit as st
import time
from datetime import datetime

# ---------------------------------------
# PAGE CONFIG
# ---------------------------------------
st.set_page_config(
    page_title="Africare - AI Health Assistant",
    page_icon="africare-log.jpg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------
# DUAL THEME SUPPORT (CSS)
# ---------------------------------------
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
        body {{
            background-color: {bg};
            color: {text};
        }}
        .main {{
            background-color: {bg};
        }}
        .stChatMessage {{
            border-radius: 12px;
            padding: 10px;
            margin-bottom: 10px;
        }}
        .stChatMessage[data-role='user'] {{
            background-color: {bubble_user};
        }}
        .stChatMessage[data-role='assistant'] {{
            background-color: {bubble_bot};
        }}
        .stButton>button {{
            background-color: #0F766E;
            color: white;
            border-radius: 10px;
            border: none;
            padding: 9px 18px;
        }}
        </style>
    """, unsafe_allow_html=True)


# ---------------------------------------
# LANGUAGE CONFIG
# ---------------------------------------
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
        "disclaimer": "This is an AI assistant. For emergencies, please contact a hospital immediately.",
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


# ---------------------------------------
# KNOWLEDGE BASE (EXPANDED)
# ---------------------------------------
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


# ---------------------------------------
# SIDEBAR
# ---------------------------------------
with st.sidebar:
    st.image("africare-log.jpg", width=130)

    st.title("Africare AI")
    st.caption("Your African Health Companion")

    # Language selector
    lang_code = st.selectbox(
        "Language",
        options=list(LANGUAGES.keys()),
        format_func=lambda x: LANGUAGES[x]
    )

    # Theme toggle
    theme = st.radio("Theme", ["Light", "Dark"])
    apply_theme(theme)

    # Offline toggle
    is_offline = st.toggle("Offline Mode", value=False)
    mode_text = TRANSLATIONS[lang_code]["offline"] if is_offline else TRANSLATIONS[lang_code]["online"]
    st.caption(f"Status: {mode_text}")

    # Clear history button
    if st.button(TRANSLATIONS[lang_code]["clear"]):
        st.session_state.messages = []
        st.success("History cleared!")

    st.divider()
    st.subheader("Verified Sources")
    st.markdown("- WHO Africa\n- Ghana Health Service\n- CDC Africa\n- UNICEF")


# ---------------------------------------
# MAIN INTERFACE
# ---------------------------------------
t = TRANSLATIONS[lang_code]

st.title(t["welcome"])
st.write(t["subtitle"])

# Initialize chat log
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input
if prompt := st.chat_input("Type your health question..."):
    # Save user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Africare is thinking..."):
            time.sleep(1)
            lower_input = prompt.lower()

            # OFFLINE MODE
            if is_offline:
                found = False
                for key in KNOWLEDGE_BASE:
                    if key in lower_input:
                        response = KNOWLEDGE_BASE[key].get(lang_code, KNOWLEDGE_BASE[key]["en"])
                        response += "\n\n*(Offline Cache)*"
                        found = True
                        break

                if not found:
                    response = "Offline mode available for Malaria, Cholera, Diabetes, Typhoid & Pregnancy only."

            # ONLINE MODE
            else:
                found = False
                for key in KNOWLEDGE_BASE:
                    if key in lower_input:
                        response = KNOWLEDGE_BASE[key].get(lang_code, KNOWLEDGE_BASE[key]["en"])
                        found = True
                        break

                if not found:
                    response = "Please consult a medical professional for accurate diagnosis. Drink water, rest, and monitor your symptoms."

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# Footer
st.markdown("---")
st.caption(t["disclaimer"])

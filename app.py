"""
Africare - Streamlit AI Health Assistant
Place africare-log.jpg beside this file.
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
    page_icon="africare-log.jpg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------
# Multilingual system prompt & dataset
# -------------------------
SYSTEM_PROMPT = """You are a Verified Health Information Assistant for Africa.
Always respond exactly in this structure and in the user's selected language:

Based on verified health information:
[Condition Name]

Symptoms: • item • item • item

Prevention: • item • item • item

Treatment: short instructions

Source: WHO / CDC / regional source

⚠️ Note: This is general health information. For diagnosis or treatment, consult a qualified healthcare provider.
"""

LANGUAGES = {
    "en": "English",
    "sw": "Swahili",
    "ak": "Akan",
    "ga": "Ga",
    "ew": "Ewe",
    "fa": "Fante"
}

TRANSLATIONS = {
    "en": {
        "welcome": "Hello! I'm Africare AI.",
        "subtitle": "Ask me anything about health (verified format)",
        "online": "Online Mode",
        "offline": "Offline Mode",
        "clear": "Clear History",
        "connection": "Connection Mode",
        "disclaimer": "This is general health information. For diagnosis or treatment, consult a qualified healthcare provider.",
        "internet_available": "Internet: Available",
        "internet_not": "Internet: Not detected",
        "mode_options": ["Auto-detect","Force Online","Force Offline"],
        "chat_placeholder": "Type your health question (e.g., 'What is malaria?')..."
    },
    "sw": {
        "welcome": "Hujambo! Mimi ni Africare AI.",
        "subtitle": "Niulize chochote kuhusu afya (muundo uliothibitishwa)",
        "online": "Mtandaoni",
        "offline": "Hali ya Nje ya Mtandao",
        "clear": "Futa Historia",
        "connection": "Hali ya Muunganisho",
        "disclaimer": "Hii ni taarifa ya afya kwa ujumla. Kwa uchunguzi au matibabu, tafadhali wasiliana na mtaalamu wa afya.",
        "internet_available": "Intaneti: Inapatikana",
        "internet_not": "Intaneti: Haipatikaniki",
        "mode_options": ["Gundua Kiotomatiki","Fungua Mtandaoni","Funga Mtandaoni"],
        "chat_placeholder": "Andika swali lako la afya (mfano: 'Malaria ni nini?')..."
    },
    "ak": {
        "welcome": "Akwaaba! Me ne Africare AI.",
        "subtitle": "Bisa me biribiara fa apɔwmuden ho (yɛ adanseɛ mu mfatoho)",
        "online": "Wɔ Intanɛt So",
        "offline": "Offline Mode",
        "clear": "Pepa Nkyerɛase",
        "connection": "Intanɛt Mɔden",
        "disclaimer": "Ɛyɛ apɔwmuden nsɛm a ɛyɛ kɛkɛ. Sɛ wopɛ ayaresabea anaa nhyira, bisa dɔkita a ɔwɔ ho.",
        "internet_available": "Intanɛt: Wɔ hɔ",
        "internet_not": "Intanɛt: Nni hɔ",
        "mode_options": ["Auto-detect","Force Online","Force Offline"],
        "chat_placeholder": "Twerɛ wo nsɛm fa apɔwmuden ho (mfatoho: 'Malaria yɛ deɛn?')..."
    },
    "ga": {
        "welcome": "Ojekoo! Mi ni Africare AI.",
        "subtitle": "Bisa me nɔ nyɛ apɔwde (verified format)",
        "online": "Online Mode",
        "offline": "Offline Mode",
        "clear": "Clear History",
        "connection": "Connection Mode",
        "disclaimer": "Mii ni nyɛ apɔwde lɛ. Ma diagnosis anaa treatment, tsɔ dɔkita.",
        "internet_available": "Internet: Available",
        "internet_not": "Internet: Not detected",
        "mode_options": ["Auto-detect","Force Online","Force Offline"],
        "chat_placeholder": "Twerɛ wo nsɛm fa apɔwmuden ho..."
    },
    "ew": {
        "welcome": "Woezɔ! Mí le Africare AI.",
        "subtitle": "Bisa me gbe sia gbe wɔ afɔdzidzi (verified format)",
        "online": "Online Mode",
        "offline": "Offline Mode",
        "clear": "Clear History",
        "connection": "Connection Mode",
        "disclaimer": "Eyi nye gbe sia gbe nu vɛ. Nɔ tsɔ dzi anyigba kple dɔkita le veviwo me.",
        "internet_available": "Internet: Available",
        "internet_not": "Internet: Not detected",
        "mode_options": ["Auto-detect","Force Online","Force Offline"],
        "chat_placeholder": "Twerɛ wo nsɛm fa apɔwmuden ho..."
    },
    "fa": {
        "welcome": "Maakye! Me ne Africare AI.",
        "subtitle": "Bisa me biribiara fa apɔwmuden ho (verified format)",
        "online": "Online Mode",
        "offline": "Offline Mode",
        "clear": "Clear History",
        "connection": "Connection Mode",
        "disclaimer": "Ɛyɛ apɔwmuden nsɛm a ɛyɛ kɛkɛ. Sɛ wopɛ ayaresabea anaa nhyira, bisa dɔkita a ɔwɔ ho.",
        "internet_available": "Internet: Available",
        "internet_not": "Internet: Not detected",
        "mode_options": ["Auto-detect","Force Online","Force Offline"],
        "chat_placeholder": "Twerɛ wo nsɛm fa apɔwmuden ho..."
    }
}

# -------------------------
# Multilingual dataset for 15 African-region diseases
# -------------------------
DISEASE_DATASET = {
    "malaria": {
        "name": {"en":"Malaria","sw":"Malaria","ak":"Malaria","ga":"Malaria","ew":"Malaria","fa":"Malaria"},
        "symptoms": {
            "en":["High fever","Chills and sweating","Headache","Nausea and vomiting","Muscle pain and fatigue"],
            "sw":["Homa kubwa","Baridi na jasho","Maumivu ya kichwa","Kuharisha na kutapika","Maumivu ya misuli na uchovu"],
            "ak":["Huraeɛ","Awɔ","Tipae","Nsusuwii ne huru","Honhom yare ne ahoɔden so apere"],
            "ga":["High fever","Chills","Headache","Nausea","Fatigue"],
            "ew":["Homa","Akɔ akɔ","Tɔwɔ le kpakple","Gbleve dzidzɔ","Agble dzidzɔ"],
            "fa":["Huraeɛ","Awɔ","Tipae","Nsusuwii ne huru","Honhom yare ne ahoɔden so apere"]
        },
        "prevention": {
            "en":["Sleep under insecticide-treated nets","Indoor spraying","Take prescribed meds","Remove standing water","Wear long clothing at dawn/dusk"],
            "sw":["Lala chini ya neti zenye dawa","Piga rangi ya ndani","Chukua dawa kama ilivyoagizwa","Ondoa maji yasiyosogea","Vaa nguo ndefu mapema na jioni"],
            "ak":["Da wɔ mosquito net so","Tɔ aduro no sɛ wɔahyɛ","Yiyi nsuo a ɛda","Twi nkuto tenten","Di ade wɔ anɔpa ne anadwo"],
            "ga":["Sleep under net","Indoor spraying","Take medicine","Remove water","Wear long clothes"],
            "ew":["Lala le net","Spray le fɔ","Tɔ medikɛshɛn","Yiyi dzidzɔ","Vɛ nglɔ nglɔ klɔts"],
            "fa":["Da wɔ mosquito net so","Tɔ aduro no sɛ wɔahyɛ","Yiyi nsuo a ɛda","Twi nkuto tenten","Di ade wɔ anɔpa ne anadwo"]
        },
        "treatment": {
            "en":["Seek immediate medical care","ACTs are recommended","Never self-medicate"],
            "sw":["Pata hospitali mara moja","Tumia ACTs kama ilivyoagizwa","Usijibadilishe dawa"],
            "ak":["Kɔ dɔkita ntɛm","Fa ACTs","Mma wo ankasa aduro"],
            "ga":["Seek care","ACTs","No self medicate"],
            "ew":["Gble dɔkita","ACTs","Metsɔ le medikɛshɛn wo fe"],
            "fa":["Kɔ dɔkita ntɛm","Fa ACTs","Mma wo ankasa aduro"]
        },
        "source":"WHO Global Health Observatory – African Region"
    },
    "cholera": {
        "name": {"en":"Cholera","sw":"Kolera","ak":"Kolera","ga":"Cholera","ew":"Cholera","fa":"Kolera"},
        "symptoms": {
            "en":["Watery diarrhea","Vomiting","Severe dehydration","Leg cramps"],
            "sw":["Kujaa kwa maji","Kutapika","Kukosa maji mwilini","Maumivu ya miguu"],
            "ak":["Nsuo yare","Tipae","Nsuo nni ho hia","Nan mu yare"],
            "ga":["Watery diarrhea","Vomiting","Severe dehydration","Leg cramps"],
            "ew":["Gbeve le tsɔdzɔ","Tɔ le kpakple","Hɔkplɔ le dzidzɔ","Leg cramps"],
            "fa":["Nsuo yare","Tipae","Nsuo nni ho hia","Nan mu yare"]
        },
        "prevention": {
            "en":["Drink safe water","Practice good hygiene","Wash hands with soap","Cook food thoroughly"],
            "sw":["Kunywa maji salama","Fanya usafi","Osha mikono","Pika chakula vizuri"],
            "ak":["Nom nsuo a ɛyɛ fɛ","Di ho dwuma pa","Ho hɔ nsuo ne sopo","Pɔkɔ aduane"],
            "ga":["Drink safe water","Good hygiene","Wash hands","Cook food"],
            "ew":["Nom dzidzɔ le afɔ","Zɔ agbɔwɔ","Fufɔ mɔ gbe","Dzudzɔ afɔ kple viɖeɖe"],
            "fa":["Nom nsuo a ɛyɛ fɛ","Di ho dwuma pa","Ho hɔ nsuo ne sopo","Pɔkɔ aduane"]
        },
        "treatment": {
            "en":["Immediate oral rehydration","Seek urgent medical care","Severe cases may need IV fluids"],
            "sw":["Tumia ORS mara moja","Pata hospitali","Matukio makali ya maji yawe IV"],
            "ak":["Fa ORS ntɛm","Kɔ dɔkita ntɛm","Nsuo pii hia IV"],
            "ga":["Oral rehydration","Seek care","IV fluids if severe"],
            "ew":["Tɔ ORS dzidzɔ","Gble dɔkita","Dzidzɔ IV le akɔ le"],
            "fa":["Fa ORS ntɛm","Kɔ dɔkita ntɛm","Nsuo pii hia IV"]
        },
        "source":"WHO Africa – Cholera Factsheet"
    },
    "tuberculosis": {
        "name": {"en":"Tuberculosis (TB)","sw":"Tuberkulosi","ak":"Tuberculosis","ga":"Tuberculosis","ew":"Tuberculosis","fa":"Tuberculosis"},
        "symptoms": {
            "en":["Persistent cough","Chest pain","Coughing blood","Weight loss","Night sweats"],
            "sw":["Kikohozi kisichopungua","Maumivu ya kifua","Kutokwa na damu","Kupoteza uzito","Jasho la usiku"],
            "ak":["Tɔ yare","Abɔdeɛ mu yare","Mogya fi ɔpono mu","Ho tɔ","Anadwo yare"],
            "ga":["Persistent cough","Chest pain","Cough blood","Weight loss","Night sweats"],
            "ew":["Gble wɔ ɖɔ","Tɔ dzidzɔ le nu","Tɔ mogya","Tɔ le wò dzidzɔ","Anɔ dzidzɔ"],
            "fa":["Tɔ yare","Abɔdeɛ mu yare","Mogya fi ɔpono mu","Ho tɔ","Anadwo yare"]
        },
        "prevention": {
            "en":["Early detection","BCG vaccination","Good ventilation","Avoid close contact with patients"],
            "sw":["Ugunduzi mapema","Chanjo ya BCG","Upepo safi","Epuka mgongano na wagonjwa"],
            "ak":["Hwehwɛ ntɛm","BCG aduru","Mframa pa","Mpɛ nsam nni yarefo ho"],
            "ga":["Early detection","BCG vaccination","Good ventilation","Avoid patients"],
            "ew":["Nɔ dzidzɔ le ɖeɖe","BCG vaccine","Good air","Avoid sick people"],
            "fa":["Hwehwɛ ntɛm","BCG aduru","Mframa pa","Mpɛ nsam nni yarefo ho"]
        },
        "treatment": {
            "en":["Seek medical evaluation","6-month antibiotic regimen","Do not stop medication early"],
            "sw":["Pata hospitali","Dawa kwa miezi 6","Usisimamishe dawa mapema"],
            "ak":["Kɔ dɔkita","Aduro mmiɛnsa mpem 6","Mma wo gyae aduro ntɛm"],
            "ga":["Seek medical care","6 month treatment","Do not stop meds"],
            "ew":["Gble dɔkita","6 month meds","Do not stop meds"],
            "fa":["Kɔ dɔkita","Aduro mmiɛnsa mpem 6","Mma wo gyae aduro ntɛm"]
        },
        "source":"WHO TB Factsheet"
    },
    "typhoid": {
        "name": {"en":"Typhoid Fever","sw":"Kifua cha Typhoid","ak":"Typhoid","ga":"Typhoid Fever","ew":"Typhoid","fa":"Typhoid Fever"},
        "symptoms": {
            "en":["High fever","Weakness and stomach pain","Constipation or diarrhea","Headache"],
            "sw":["Homa kubwa","Uchovu na maumivu ya tumbo","Kutapika au kuharisha","Maumivu ya kichwa"],
            "ak":["Huraeɛ","Ho dɔ ne ɔkɔtɔ mu yare","Muka anaa nsuo yare","Tipae"],
            "ga":["High fever","Weakness","Constipation/Diarrhea","Headache"],
            "ew":["Homa","Akɔ akɔ","Gble/Watery stools","Tɔwɔ le kpakple"],
            "fa":["Huraeɛ","Ho dɔ ne ɔkɔtɔ mu yare","Muka anaa nsuo yare","Tipae"]
        },
        "prevention": {
            "en":["Drink clean water","Wash hands","Eat properly cooked food","Get vaccinated if available"],
            "sw":["Kunywa maji safi","Osha mikono","Pika chakula vizuri","Pata chanjo"],
            "ak":["Nom nsuo fɛfɛɛfɛ","Ho hɔ nsuo","Pɔkɔ aduane","Fa aduru"],
            "ga":["Drink water","Wash hands","Cook food","Vaccinate if possible"],
            "ew":["Nom dzidzɔ","Fufɔ mɔ","Dzudzɔ afɔ","Vaccine le gbɔ"],
            "fa":["Nom nsuo fɛfɛɛfɛ","Ho hɔ nsuo","Pɔkɔ aduane","Fa aduru"]
        },
        "treatment": {
            "en":["Seek prompt medical treatment","Take antibiotics as prescribed"],
            "sw":["Pata matibabu mara moja","Chukua antibiotics kama ilivyoagizwa"],
            "ak":["Kɔ dɔkita ntɛm","Fa aduro sɛ wɔahyɛ"],
            "ga":["Seek care","Take antibiotics"],
            "ew":["Gble dɔkita","Tɔ antibiotics"],
            "fa":["Kɔ dɔkita ntɛm","Fa aduro sɛ wɔahyɛ"]
        },
        "source":"WHO Typhoid Factsheet"
    }
    # Repeat similar blocks for: Dengue, Hepatitis B, Measles, COVID-19, Ebola, Lassa Fever, Yellow Fever, Schistosomiasis, Trachoma, Onchocerciasis, HIV/AIDS
}

# -------------------------
# Theme
# -------------------------
def apply_theme(theme):
    if theme == "Light":
        bg="#f7fafc"; text="#0f172a"; user_bubble="#DCF8C6"; bot_bubble="#ffffff"
    else:
        bg="#0b1220"; text="#e6eef8"; user_bubble="#1f2937"; bot_bubble="#0b1220"
    st.markdown(f"""
    <style>
    .stApp {{background-color:{bg}; color:{text};}}
    .stButton>button {{background-color:#0F766E;color:white;border-radius:10px;padding:8px 16px;}}
    .chat-user {{background:{user_bubble};padding:10px;border-radius:12px;margin-bottom:4px;}}
    .chat-bot {{background:{bot_bubble};padding:10px;border-radius:12px;margin-bottom:4px;}}
    </style>""",unsafe_allow_html=True)

# -------------------------
# Internet check
# -------------------------
def check_internet(timeout=2):
    try: r=requests.get("https://www.google.com",timeout=timeout); return r.status_code==200
    except: return False
if "internet_available" not in st.session_state: st.session_state.internet_available = check_internet()

# -------------------------
# LLM keys
# -------------------------
OPENAI_KEY=os.environ.get("OPENAI_API_KEY","").strip()
GROQ_KEY=os.environ.get("GROQ_API_KEY","").strip()
GEMINI_KEY=os.environ.get("GEMINI_API_KEY","").strip()

# -------------------------
# LLM Wrappers
# -------------------------
def call_openai(system_prompt,user_prompt):
    if not OPENAI_KEY: raise RuntimeError("OpenAI key not set.")
    try:
        import openai
        openai.api_key=OPENAI_KEY
        resp=openai.ChatCompletion.create(model="gpt-4o-mini",messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],temperature=0.1,max_tokens=512)
        return resp.choices[0].message.content.strip()
    except: return "Error calling OpenAI."

def call_groq(system_prompt,user_prompt): return "Groq placeholder."
def call_gemini(system_prompt,user_prompt): return "Gemini placeholder."

# -------------------------
# Chat helpers
# -------------------------
def find_disease(query):
    q=query.lower()
    for key,info in DISEASE_DATASET.items():
        if key in q or any(q in n.lower() for n in info["name"].values()):
            return info
    return None

def format_health(info,lang="en"):
    s=" • ".join(info["symptoms"].get(lang,info["symptoms"]["en"]))
    p=" • ".join(info["prevention"].get(lang,info["prevention"]["en"]))
    t=" • ".join(info["treatment"].get(lang,info["treatment"]["en"]))
    text=f"Based on verified health information:\n{info['name'].get(lang,info['name']['en'])}\n\nSymptoms: • {s}\n\nPrevention: • {p}\n\nTreatment: • {t}\n\nSource: {info.get('source','WHO')}\n\n⚠️ Note: This is general health information. For diagnosis or treatment, consult a qualified healthcare provider."
    return text

def generate_response(user_text,lang="en",force_offline=False):
    dataset_info=find_disease(user_text)
    if force_offline or not st.session_state.internet_available or not any([OPENAI_KEY,GROQ_KEY,GEMINI_KEY]):
        if dataset_info: return format_health(dataset_info,lang)
        return "Information not available offline. Please consult a healthcare provider."
    for fn in [call_openai,call_gemini,call_groq]:
        try:
            text=fn(SYSTEM_PROMPT,user_text)
            if dataset_info: return format_health(dataset_info,lang)
            return text
        except: continue
    if dataset_info: return format_health(dataset_info,lang)
    return "Unable to retrieve online info. Please consult a healthcare provider."

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.image("africare.jpg", width=140)
    st.title("Africare AI")
    st.caption("Your African Health Companion")
    lang=st.selectbox("Language",options=list(LANGUAGES.keys()),format_func=lambda x:LANGUAGES[x])
    theme=st.radio("Theme",["Light","Dark"],index=0)
    apply_theme(theme)
    st.markdown("### "+TRANSLATIONS[lang]["connection"])
    conn_mode=st.selectbox("",options=TRANSLATIONS[lang]["mode_options"])
    if conn_mode==TRANSLATIONS[lang]["mode_options"][1]: force_offline=False
    elif conn_mode==TRANSLATIONS[lang]["mode_options"][2]: force_offline=True
    else: force_offline=not st.session_state.internet_available
    if st.button(TRANSLATIONS[lang]["clear"]):
        st.session_state.messages=[]
    st.markdown("---")
    st.subheader("Verified Sources")
    st.markdown("- WHO Africa\n- Ghana Health Service\n- CDC Africa\n- UNICEF")

# -------------------------
# Chat display
# -------------------------
if "messages" not in st.session_state: st.session_state.messages=[]
st.title(TRANSLATIONS[lang]["welcome"])
st.write(TRANSLATIONS[lang]["subtitle"])
for msg in st.session_state.messages:
    role=msg.get("role","assistant"); content=msg.get("content","")
    if role=="user": st.markdown(f"<div class='chat-user'><b>You:</b><br>{content}</div>",unsafe_allow_html=True)
    else: st.markdown(f"<div class='chat-bot'><b>Africare:</b><br>{content}</div>",unsafe_allow_html=True)
prompt=st.chat_input(TRANSLATIONS[lang]["chat_placeholder"])
if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
    response=generate_response(prompt,lang=lang,force_offline=force_offline)
    st.session_state.messages.append({"role":"assistant","content":response})
    st.experimental_rerun()
st.markdown("---")
st.caption(TRANSLATIONS[lang]["disclaimer"])

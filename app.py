# africare_rag_streamlit.py
import os
import time
import json
import requests
from pathlib import Path
from typing import List, Tuple
import streamlit as st

# optional imports (embedding + vector store)
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    EMBEDDINGS_AVAILABLE = True
except Exception:
    EMBEDDINGS_AVAILABLE = False

# text extraction from PDFs
try:
    import PyPDF2
    PDF_LIB = True
except Exception:
    PDF_LIB = False

# sklearn fallback
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(
    page_title="Africare - RAG Health Assistant",
    page_icon="africare-logo.jpg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# THEME CSS
# -------------------------
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
    .sidebar .stImage img {{ border-radius: 8px; }}
    </style>
    """, unsafe_allow_html=True)

# -------------------------
# LANGUAGES / TRANSLATIONS
# -------------------------
LANGUAGES = {"en": "English", "ak": "Akan", "sw": "Swahili", "ga": "Ga", "ew": "Ewe", "fa": "Fante"}
TRANSLATIONS = {
    "en": {"welcome": "Hello! I'm Africare AI.", "subtitle": "Ask me anything about health.",
           "offline": "Offline Mode", "online": "Online Mode",
           "disclaimer": "This is an AI assistant. For emergencies, contact a hospital immediately.", "clear": "Clear History"},
    "sw": {"welcome": "Hujambo! Mimi ni Africare AI.", "subtitle": "Niulize chochote kuhusu afya.",
           "offline": "Hali ya Nje ya Mtandao", "online": "Mtandaoni",
           "disclaimer": "Hii ni AI. Kwa dharura, tembelea hospitali.", "clear": "Futa Mawasiliano"},
    "ak": {"welcome": "Akwaaba! Me ne Africare AI.", "subtitle": "Bisa me biribiara fa apɔwmuden ho.",
           "offline": "Offline Mode", "online": "Wɔ Intanɛt So",
           "disclaimer": "Sɛ woyare pa ara a, kɔ asɔpiti.", "clear": "Pepa Abesua"}
}

# -------------------------
# SIMPLE HEALTH DATASET (fallback & KB)
# -------------------------
HEALTH_DATASET = {
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
        "treatment": "Seek immediate medical care. First-line treatment includes artemisinin-based combination therapies (ACTs). Never self-medicate.",
        "source": "WHO Global Health Observatory – African Region"
    },
    # ... (Add other dataset entries if desired; omitted here for brevity)
}

# -------------------------
# RAG: Load local WHO PDFs
# -------------------------
PDF_FOLDER = Path("who_pdfs")
PDF_FOLDER.mkdir(exist_ok=True)

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extracts text from a PDF using PyPDF2. If not available or fails, returns empty string.
    """
    if not PDF_LIB:
        return ""
    text_chunks = []
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                try:
                    text = page.extract_text()
                    if text:
                        text_chunks.append(text)
                except Exception:
                    continue
    except Exception:
        return ""
    return "\n".join(text_chunks)

def load_documents_from_pdfs(folder: Path) -> List[Tuple[str, str]]:
    """
    Returns a list of (doc_id, text) tuples from PDFs in folder.
    doc_id will be the filename.
    """
    docs = []
    for pdf_file in folder.glob("*.pdf"):
        text = extract_text_from_pdf(pdf_file)
        if text and len(text.strip())>50:
            docs.append((pdf_file.name, text))
    return docs

# -------------------------
# SPLIT TEXT INTO CHUNKS
# -------------------------
def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> List[str]:
    """Simple character-based splitter that keeps overlap to preserve context."""
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(start + max_chars, L)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == L:
            break
        start = max(end - overlap, end)
    return chunks

# -------------------------
# VECTOR INDEX BUILDERS / FALLBACK
# -------------------------
class RAGIndex:
    def __init__(self, docs: List[Tuple[str,str]]):
        """
        docs: list of (doc_id, text)
        builds either FAISS+sentence-transformers or TF-IDF+NearestNeighbors index
        """
        self.documents = []   # list of {"id":docid, "text": text, "chunk_id": id}
        for doc_id, text in docs:
            for i, chunk in enumerate(chunk_text(text)):
                self.documents.append({"id": doc_id, "chunk_id": i, "text": chunk})

        self.use_embeddings = EMBEDDINGS_AVAILABLE
        if self.use_embeddings:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                texts = [d["text"] for d in self.documents]
                self.embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
                dim = self.embeddings.shape[1]
                self.index = faiss.IndexFlatL2(dim)
                self.index.add(self.embeddings)
            except Exception:
                # fallback to TF-IDF
                self.use_embeddings = False

        if not self.use_embeddings:
            # TF-IDF fallback
            self.vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
            texts = [d["text"] for d in self.documents]
            if texts:
                self.doc_term = self.vectorizer.fit_transform(texts)
                self.nn = NearestNeighbors(n_neighbors=5, metric="cosine").fit(self.doc_term)
            else:
                self.doc_term = None
                self.nn = None

    def retrieve(self, query: str, top_k: int = 4) -> List[dict]:
        """
        Returns top_k document chunks as list of dicts {"id","chunk_id","text","score"}
        """
        if len(self.documents) == 0:
            return []

        if self.use_embeddings:
            q_emb = self.model.encode([query], convert_to_numpy=True)
            dists, idxs = self.index.search(q_emb, top_k)
            results = []
            for dist, idx in zip(dists[0], idxs[0]):
                if idx < len(self.documents):
                    results.append({"id": self.documents[idx]["id"], "chunk_id": self.documents[idx]["chunk_id"], "text": self.documents[idx]["text"], "score": float(dist)})
            return results
        else:
            if self.doc_term is None or self.nn is None:
                return []
            q_vec = self.vectorizer.transform([query])
            dists, idxs = self.nn.kneighbors(q_vec, n_neighbors=min(top_k, len(self.documents)))
            results = []
            for dist_row, idx_row in zip(dists, idxs):
                for dist, idx in zip(dist_row, idx_row):
                    results.append({"id": self.documents[idx]["id"], "chunk_id": self.documents[idx]["chunk_id"], "text": self.documents[idx]["text"], "score": float(dist)})
            # sort by ascending distance (better matches first)
            results = sorted(results, key=lambda x: x["score"])
            return results

# -------------------------
# Build (or cache) RAG index on startup
# -------------------------
if "rag_index" not in st.session_state:
    docs = load_documents_from_pdfs(PDF_FOLDER)
    st.session_state._who_pdf_files = [d[0] for d in docs]
    if docs:
        st.session_state.rag_index = RAGIndex(docs)
        st.session_state.rag_ready = True
    else:
        st.session_state.rag_index = None
        st.session_state.rag_ready = False

# -------------------------
# LLM PROVIDER ADAPTERS
# -------------------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()

def is_online(timeout=2):
    test_urls = ["https://api.openai.com/v1/models", "https://www.google.com"]
    for url in test_urls:
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code in (200, 401, 403):
                return True
        except Exception:
            continue
    return False

# cache internet detection
if "internet_available" not in st.session_state:
    st.session_state.internet_available = is_online()

def call_openai_chat(system_prompt: str, user_prompt: str, model="gpt-3.5-turbo"):
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI key missing")
    try:
        import openai
        openai.api_key = OPENAI_KEY
        messages = [{"role":"system","content": system_prompt}, {"role":"user","content": user_prompt}]
        resp = openai.ChatCompletion.create(model=model, messages=messages, max_tokens=512, temperature=0.2)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # fallback to HTTP
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages":[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}], "max_tokens":512, "temperature":0.2}
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

def call_groq(...):
    # Placeholder: user should implement with real Groq SDK/HTTP shape
    raise NotImplementedError("Groq call not implemented here; provide endpoint & parsing.")

def call_gemini(...):
    # Placeholder: user should implement with real Gemini SDK/HTTP shape
    raise NotImplementedError("Gemini call not implemented here; provide endpoint & parsing.")

def call_providers(system_prompt: str, augmented_prompt: str, providers_order: List[str]):
    errors = {}
    for p in providers_order:
        try:
            if p == "openai" and OPENAI_KEY:
                return call_openai_chat(system_prompt, augmented_prompt)
            if p == "groq" and GROQ_KEY:
                return call_groq(system_prompt, augmented_prompt)
            if p == "gemini" and GEMINI_KEY:
                return call_gemini(system_prompt, augmented_prompt)
        except Exception as e:
            errors[p] = str(e)
            continue
    # If none available or all errors: return None to indicate fallback
    return None

# -------------------------
# SYSTEM PROMPT (Verified health format)
# -------------------------
SYSTEM_PROMPT = """
You are Africare — an African Health Assistant. ALWAYS format every health-related answer in this exact verified structure:

[Condition Name]

Symptoms:
• symptom 1
• symptom 2
• symptom 3

Prevention:
• prevention tip 1
• prevention tip 2

Treatment:
Clear, safe medical guidance including when to seek professional care. Do NOT encourage self-medication.

Source: WHO / Africa CDC / CDC / National Health Service (choose most relevant if available)

⚠️ Note: This is general health information. For diagnosis & treatment, consult a qualified healthcare provider.

When relevant, prioritize and cite information from the provided WHO PDFs (local documents) in the 'Source' line. If you use local WHO PDFs, include the PDF filename(s) in the Source field.
"""

# -------------------------
# Helper: Build augmented prompt using top retrieved docs
# -------------------------
def build_augmented_prompt(user_question: str, rag_index: RAGIndex, top_k:int=3, lang="en") -> Tuple[str, List[dict]]:
    """
    Returns (augmented_prompt, retrieved_docs_list)
    """
    retrieved = []
    if rag_index and st.session_state.rag_ready:
        retrieved = rag_index.retrieve(user_question, top_k=top_k)

    # Compose context string from retrieved docs
    context_pieces = []
    used_files = set()
    for r in retrieved:
        context_pieces.append(f"---\nSourceFile: {r['id']} (chunk {r['chunk_id']})\n{r['text'][:1500]}\n---")
        used_files.add(r['id'])

    context_block = "\n\n".join(context_pieces) if context_pieces else ""

    augmented = f"{SYSTEM_PROMPT}\n\nUser question: {user_question}\n\nContext from local WHO PDFs:\n{context_block}\n\nAnswer in the required structure and cite sources (use filenames if using local PDFs)."
    return augmented, [{"file": f} for f in used_files]

# -------------------------
# Format dataset entry into verified template (fallback)
# -------------------------
def format_dataset_entry(entry: dict) -> str:
    symptoms = "\n• ".join(entry.get("symptoms", []))
    prevention = "\n• ".join(entry.get("prevention", []))
    treatment = entry.get("treatment", "")
    source = entry.get("source", "WHO")
    formatted = f"""{entry.get('name')}

Symptoms:
• {symptoms}

Prevention:
• {prevention}

Treatment:
{treatment}

Source: {source}

⚠️ Note: This is general health information. For diagnosis and treatment, consult a qualified healthcare provider."""
    return formatted

def fallback_to_dataset(query: str) -> str:
    q = query.lower()
    for key, entry in HEALTH_DATASET.items():
        if key in q:
            return format_dataset_entry(entry)
    return ("I could not find a direct match in the local dataset. "
            "Try a more specific condition name, or consult the 'Verified Sources' listed in the sidebar.")

# -------------------------
# STREAMLIT UI: Sidebar
# -------------------------
with st.sidebar:
    # logo
    if Path("africare-logo.jpg").exists():
        st.image("africare-logo.jpg", width=140)
    else:
        st.caption("Place africare-logo.jpg next to this script to show the logo.")

    st.title("Africare RAG")
    st.caption("AI Health Assistant — Local WHO PDF RAG")

    lang_code = st.selectbox("Language", options=list(LANGUAGES.keys()), format_func=lambda x: LANGUAGES[x])
    theme_choice = st.radio("Theme", ["Light", "Dark"], index=0)
    apply_theme(theme_choice)

    # show rag readiness
    if st.session_state.rag_ready:
        st.success(f"RAG ready — {len(st.session_state._who_pdf_files)} PDF(s) indexed: {', '.join(st.session_state._who_pdf_files)}")
    else:
        st.warning("No WHO PDFs loaded. Put PDFs into ./who_pdfs/ and refresh the app to enable RAG.")

    # connection auto-detect + override
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
    st.markdown("Provide API keys via env vars: OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY")
    providers_order = st.multiselect("Provider order (top→bottom)", ["openai","gemini","groq"], default=["openai","gemini","groq"])

    st.divider()
    if st.button(TRANSLATIONS[lang_code]["clear"]):
        st.session_state.messages = []
        st.success("History cleared!")

    st.divider()
    st.subheader("Verified Sources")
    st.markdown("- Local WHO PDFs (if loaded)\n- WHO\n- Africa CDC\n- Ghana Health Service\n- CDC")

# -------------------------
# MAIN: Chat area
# -------------------------
st.title(TRANSLATIONS[lang_code]["welcome"])
st.write(TRANSLATIONS[lang_code]["subtitle"])

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Input
user_input = st.chat_input("Type your health question (e.g., 'What is malaria?')...")

if user_input:
    # Save user
    st.session_state.messages.append({"role":"user","content":user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Africare searching local WHO PDFs and composing response..."):
            time.sleep(0.6)

            # Build augmented prompt using local RAG
            rag_index = st.session_state.rag_index if st.session_state.rag_ready else None
            augmented_prompt, used_files = build_augmented_prompt(user_input, rag_index, top_k=4, lang=lang_code)

            response_text = None
            if is_offline:
                # offline -> prefer local dataset then RAG retrieved content (no LLM)
                if rag_index and st.session_state.rag_ready:
                    # try to answer by returning retrieved context + instruction to user
                    retrieved = rag_index.retrieve(user_input, top_k=4)
                    if retrieved:
                        # Try to synthesize a succinct reply by showing context and dataset match
                        # We'll try to find a matching HEALTH_DATASET entry first
                        ds = fallback_to_dataset(user_input)
                        # Compose reply: prioritize dataset entry + retrieved excerpts
                        ctxs = "\n\n".join([f"From {r['id']} (chunk {r['chunk_id']}):\n{r['text'][:800]}..." for r in retrieved])
                        response_text = f"Based on verified local WHO documents and our dataset:\n\n{ds}\n\nRelevant excerpts from local WHO PDFs:\n{ctxs}\n\nSource: {', '.join({r['id'] for r in retrieved})}\n\n⚠️ Note: This is general information. Consult a qualified healthcare provider."
                    else:
                        response_text = fallback_to_dataset(user_input)
                else:
                    # No RAG -> dataset fallback
                    response_text = fallback_to_dataset(user_input)
            else:
                # Online -> try LLM providers with augmented prompt
                order = providers_order or ["openai","gemini","groq"]
                try:
                    llm_out = call_providers(SYSTEM_PROMPT, augmented_prompt, order)
                    if llm_out:
                        response_text = llm_out
                    else:
                        # LLM not available or failed -> fallback to dataset + retrieved context
                        if rag_index and st.session_state.rag_ready:
                            retrieved = rag_index.retrieve(user_input, top_k=4)
                            if retrieved:
                                ctxs = "\n\n".join([f"From {r['id']} (chunk {r['chunk_id']})\n{r['text'][:1000]}..." for r in retrieved])
                                ds = fallback_to_dataset(user_input)
                                response_text = f"{ds}\n\nRelevant local excerpts:\n{ctxs}\n\nSource: {', '.join({r['id'] for r in retrieved})}\n\n⚠️ Note: This is general information."
                            else:
                                response_text = fallback_to_dataset(user_input)
                        else:
                            response_text = fallback_to_dataset(user_input)
                except Exception as e:
                    response_text = f"Error calling remote LLMs: {str(e)}\n\nFalling back to local dataset.\n\n" + fallback_to_dataset(user_input)

            # Display & store
            st.markdown(response_text)
            st.session_state.messages.append({"role":"assistant","content":response_text})

# Footer
st.markdown("---")
st.caption(TRANSLATIONS[lang_code]["disclaimer"])

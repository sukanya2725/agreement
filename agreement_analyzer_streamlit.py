import streamlit as st
import fitz  # PyMuPDF
import re
import tempfile
import base64
import time
from gtts import gTTS
from rapidfuzz import fuzz

st.set_page_config(page_title="Agreement Analyzer", layout="centered")

# ✅ Duolingo Bird GIF
bird_gif = "https://i.postimg.cc/2jtSq2gC/duolingo-meme-flying-bird-kc0czqsh6zrv6aqv.gif"

# --- CSS for bird movement ---
st.markdown(f"""
<style>
.bird {{
    position: absolute;
    width: 90px;
    z-index: 999;
    animation-duration: 2.5s;
}}

.fly-header {{
    top: 20px; left: 30px;
}}

.fly-upload {{
    animation-name: flyToUpload;
}}

.fly-audio {{
    animation-name: flyToAudio;
}}

@keyframes flyToUpload {{
  0% {{ top: 20px; left: 30px; }}
  100% {{ top: 300px; left: 120px; }}
}}

@keyframes flyToAudio {{
  0% {{ top: 300px; left: 120px; }}
  100% {{ top: 680px; left: 150px; }}
}}

</style>
""", unsafe_allow_html=True)

# --- Speak Function ---
def speak(text):
    tts = gTTS(text, lang='en')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        with open(fp.name, "rb") as audio_file:
            b64 = base64.b64encode(audio_file.read()).decode()
            audio_html = f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
    time.sleep(2)

# --- App Header ---
st.markdown("<h1 style='text-align:center; color:#2c3e50;'>📄 Agreement Analyzer</h1>", unsafe_allow_html=True)

# --- Bird Step 1: Welcome ---
st.markdown(f"""<div class="bird fly-header"><img src="{bird_gif}" width="90"></div>""", unsafe_allow_html=True)
speak("Welcome to my app")
time.sleep(1)

# --- Bird Step 2: Fly to Upload Button ---
st.markdown(f"""<div class="bird fly-upload"><img src="{bird_gif}" width="90"></div>""", unsafe_allow_html=True)
speak("Upload your document here")
time.sleep(1)

# --- File Upload ---
uploaded_file = st.file_uploader("📤 Upload Agreement (PDF)", type=["pdf"])

if uploaded_file:
    speak("Thank you. Processing your document.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    doc = fitz.open(pdf_path)
    text = " ".join([page.get_text() for page in doc])
    text = re.sub(r'\s+', ' ', text)

    def smart_search(text, keywords):
        best = "Not specified"
        score = 0
        segments = re.split(r'(?<=[.!?])\s+', text)
        for keyword in keywords:
            for segment in segments:
                s = fuzz.partial_ratio(keyword.lower(), segment.lower())
                if s > score and s > 70:
                    score = s
                    best = segment
        return best

    project_name = smart_search(text, ["project title", "name of work", "tender for"])
    scope = smart_search(text, ["scope of work", "work includes"])
    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    date = date_match.group(0) if date_match else "Not specified"
    amount_sentence = smart_search(text, ["contract value", "estimated cost"])
    amount_match = re.search(r'(?:Rs\.?|₹)?\s*[\d,]+(?:\.\d{1,2})?', amount_sentence)
    amount = amount_match.group(0) if amount_match else amount_sentence
    parties = smart_search(text, ["between", "municipal corporation", "contractor"])
    duration = smart_search(text, ["calendar months", "completion time", "within"])

    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure"],
        "Termination": ["termination", "terminate"],
        "Dispute Resolution": ["arbitration", "dispute"],
        "Jurisdiction": ["jurisdiction", "court"],
        "Force Majeure": ["force majeure"],
        "Signatures": ["signed by", "signature"]
    }

    clause_results = [f"✅ {k}" if smart_search(text, v) != "Not specified" else f"❌ {k}" for k, v in clauses.items()]

    paragraph = f"This agreement"
    if parties != "Not specified": paragraph += f" is made between {parties}"
    if date != "Not specified": paragraph += f" on {date}"
    if project_name != "Not specified": paragraph += f" for the project: {project_name}"
    if scope != "Not specified": paragraph += f", covering: {scope}"
    if amount != "Not specified": paragraph += f". The contract value is {amount}"
    if duration != "Not specified": paragraph += f", with a duration of {duration}."
    if any(c.startswith("✅") for c in clause_results):
        paragraph += " Clauses include: " + ", ".join([c[2:] for c in clause_results if c.startswith("✅")]) + "."

    # --- Bird Step 3: Fly to Audio Section ---
    st.markdown(f"""<div class="bird fly-audio"><img src="{bird_gif}" width="90"></div>""", unsafe_allow_html=True)
    speak("Here is your output. Click below to listen to summary. Thank you.")
    time.sleep(1)

    # --- Display Summary ---
    st.markdown(f"""
    <div style="background:#fff7d1;padding:1.2rem;border-radius:10px;margin-top:1rem">
        <h3 style="color:#003366">📌 Project:</h3><p>{project_name}</p>
        <h3 style="color:#003366">📅 Date:</h3><p>{date}</p>
        <h3 style="color:#003366">👥 Parties:</h3><p>{parties}</p>
        <h3 style="color:#003366">💰 Amount:</h3><p>{amount}</p>
        <h3 style="color:#003366">📦 Scope:</h3><p>{scope}</p>
        <h3 style="color:#003366">⏱ Duration:</h3><p>{duration}</p>
        <h3 style="color:#003366">🧾 Clauses:</h3><p>{'<br>'.join(clause_results)}</p>
        <h3 style="color:#003366">🧠 Summary:</h3><p>{paragraph}</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Play Summary Audio ---
    tts = gTTS(paragraph[:3900], lang='en')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
        tts.save(audio_file.name)
        with open(audio_file.name, "rb") as f:
            b64_audio = base64.b64encode(f.read()).decode()
            st.markdown(f"""
            <div style="margin-top:20px">
                <audio controls>
                    <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
                </audio>
            </div>
            """, unsafe_allow_html=True)

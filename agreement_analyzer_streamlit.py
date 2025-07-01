import streamlit as st
import fitz  # PyMuPDF
import re
import tempfile
import base64
import time
from gtts import gTTS
from rapidfuzz import fuzz

st.set_page_config(page_title="Agreement Analyzer", layout="centered")

# --- Session State Flags ---
if "bird_stage" not in st.session_state:
    st.session_state.bird_stage = "fly-header"
if "welcome_done" not in st.session_state:
    st.session_state.welcome_done = False
if "upload_done" not in st.session_state:
    st.session_state.upload_done = False
if "summary_done" not in st.session_state:
    st.session_state.summary_done = False

bird_gif = "https://i.postimg.cc/2jtSq2gC/duolingo-meme-flying-bird-kc0czqsh6zrv6aqv.gif"

# --- CSS Styling ---
st.markdown(f"""
<style>
.bird {{
    position: absolute;
    width: 90px;
    z-index: 999;
}}
@keyframes flyToUpload {{
  0% {{ top: 20px; left: 30px; }}
  100% {{ top: 270px; left: 160px; }}
}}
@keyframes flyToAudio {{
  0% {{ top: 270px; left: 160px; }}
  100% {{ top: 960px; left: 160px; }}
}}
.card-flip {{
  background: transparent;
  width: 100%;
  perspective: 1000px;
  margin-top: 2rem;
}}
.card-inner {{
  position: relative;
  width: 100%;
  transition: transform 1s;
  transform-style: preserve-3d;
}}
.card-flip:hover .card-inner {{
  transform: rotateY(180deg);
}}
.card-front, .card-back {{
  position: absolute;
  width: 100%;
  backface-visibility: hidden;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 0 15px rgba(0,0,0,0.15);
}}
.card-front {{
  background-color: #fff7d1;
  color: #333;
}}
.card-back {{
  background-color: #e1f5fe;
  transform: rotateY(180deg);
  color: #004d40;
}}
</style>
""", unsafe_allow_html=True)

# --- Bird Positioning ---
bird_position = {
    "fly-header": "top: 20px; left: 30px;",
    "fly-upload": "top: 270px; left: 160px;",
    "fly-audio": "top: 960px; left: 160px;"
}
style = bird_position.get(st.session_state.bird_stage, "top: 20px; left: 30px;")
st.markdown(f"""
<div class="bird" style="{style}; background: none !important;">
    <img src="{bird_gif}" width="90" style="background: transparent !important;">
</div>
""", unsafe_allow_html=True)

# --- Speak Function ---
def speak(text):
    tts = gTTS(text, lang='en')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        with open(fp.name, "rb") as audio_file:
            b64 = base64.b64encode(audio_file.read()).decode()
            st.markdown(f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """, unsafe_allow_html=True)
    time.sleep(2)

# --- Title ---
st.markdown("<h1 style='text-align:center; color:#2c3e50;'>📄 Agreement Analyzer</h1>", unsafe_allow_html=True)

# --- Welcome Voice ---
if not st.session_state.welcome_done:
    speak("Welcome to my app")
    st.session_state.welcome_done = True
    st.session_state.bird_stage = "fly-upload"

# --- File Upload ---
uploaded_file = st.file_uploader("📤 Upload Agreement (PDF)", type=["pdf"])
if uploaded_file:
    if not st.session_state.upload_done:
        speak("Upload your document here")
        time.sleep(1.5)
        speak("Thank you. Processing your document.")
        st.session_state.upload_done = True
        st.session_state.bird_stage = "fly-audio"

    # --- Read PDF ---
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    doc = fitz.open(pdf_path)
    text = " ".join([page.get_text() for page in doc])
    text = re.sub(r'\s+', ' ', text)

    # --- Extraction ---
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

    # --- Summary Voice ---
    if not st.session_state.summary_done:
        speak("Here is your output.")
        st.session_state.summary_done = True

    # --- Flip Card ---
    st.markdown(f"""
    <div class="card-flip">
      <div class="card-inner">
        <div class="card-front">
            <h3>📌 Project:</h3><p>{project_name}</p>
            <h3>📅 Date:</h3><p>{date}</p>
            <h3>👥 Parties:</h3><p>{parties}</p>
            <h3>💰 Amount:</h3><p>{amount}</p>
            <h3>📦 Scope:</h3><p>{scope}</p>
            <h3>⏱ Duration:</h3><p>{duration}</p>
        </div>
        <div class="card-back">
            <h3>🧾 Clauses:</h3><p>{'<br>'.join(clause_results)}</p>
            <h3>🧠 Summary:</h3><p>{paragraph}</p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Bird speaks when it lands on audio section ---
    if st.session_state.bird_stage == "fly-audio":
        speak("Click below to listen to summary")

    # --- Audio Summary ---
    tts = gTTS(paragraph[:3900], lang='en')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
        tts.save(audio_file.name)
        with open(audio_file.name, "rb") as f:
            b64_audio = base64.b64encode(f.read()).decode()

    st.markdown(f"""
    <div style="margin-top:10px; text-align:center;">
        <h4>🔉 Listen to the Summary</h4>
        <audio controls>
            <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
        </audio>
    </div>
    """, unsafe_allow_html=True)

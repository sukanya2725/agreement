import streamlit as st
import pymupdf as fitz
import os
import re
from gtts import gTTS
from deep_translator import GoogleTranslator
import tempfile
import base64
from rapidfuzz import fuzz
import textwrap
import time

st.set_page_config(page_title="Agreement Analyzer", layout="centered")

bird_img_url = "https://cdn.pixabay.com/animation/2023/01/24/20/21/20-21-56-279_512.gif"

# --- Styling with Bird Movement ---
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Poppins', sans-serif;
    background-color: #fffde7;
}}

h1, h2, h3 {{
    font-weight: 600;
}}

.block-container {{
    padding: 2rem;
    animation: fadeInUp 0.8s ease-in-out;
}}

@keyframes fly1 {{
  from {{ transform: translate(0, 0); }}
  to {{ transform: translate(100px, 40px); }}
}}

@keyframes fly2 {{
  from {{ transform: translate(0, 0); }}
  to {{ transform: translate(100px, 60px); }}
}}

@keyframes fly3 {{
  from {{ transform: translate(0, 0); }}
  to {{ transform: translate(100px, 80px); }}
}}

.bird-fly-1, .bird-fly-2, .bird-fly-3 {{
  position: absolute;
  width: 60px;
  height: auto;
  z-index: 100;
}}

.bird-fly-1 {{
  animation: fly1 2s forwards;
  left: 0; top: 20px;
}}

.bird-fly-2 {{
  animation: fly2 2s forwards 2s;
  left: 100px; top: 60px;
}}

.bird-fly-3 {{
  animation: fly3 2s forwards 4s;
  left: 200px; top: 120px;
}}

@keyframes fadeInUp {{
    0% {{ transform: translateY(20px); opacity: 0; }}
    100% {{ transform: translateY(0); opacity: 1; }}
}}

section[data-testid="stFileUploader"] > label {{
    display: block;
    background: linear-gradient(to right, #fff8dc, #fff3b0);
    padding: 1.2rem;
    border-radius: 16px;
    border: 2px dashed #e6b800;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    margin-top: 1.5rem;
    transition: all 0.3s ease;
}}

section[data-testid="stFileUploader"] > label:hover {{
    background: #fff1a8;
    border-color: #cc9900;
    cursor: pointer;
}}

.bird-message {{
    background: #f9f9f9;
    padding: 10px 20px;
    margin: 15px 0;
    border-left: 5px solid #ffb300;
    font-size: 1rem;
    font-weight: bold;
    border-radius: 8px;
    color: #4e342e;
    animation: fadeInUp 0.5s ease-in-out;
}}
</style>
""", unsafe_allow_html=True)

# --- Bird speaks audio ---
def bird_speaks(text):
    try:
        tts = gTTS(text, lang='en')
        path = os.path.join(tempfile.gettempdir(), "bird_voice.mp3")
        tts.save(path)
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """, unsafe_allow_html=True)
        time.sleep(3)
    except:
        pass

# --- Initial Instruction ---
st.markdown(f"""
<div class="bird-fly-1">
    <img src="{bird_img_url}" width="60"/>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="bird-message">🐦 Hello! Please upload your agreement file by clicking the browse button.</div>', unsafe_allow_html=True)
bird_speaks("Hello! Please upload your agreement file by clicking on the browse file button")

# --- File Upload ---
uploaded_file = st.file_uploader("📤 Upload a PDF Agreement", type=["pdf"])

if uploaded_file:
    st.markdown(f"""
    <div class="bird-fly-2">
        <img src="{bird_img_url}" width="60"/>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="bird-message">🐦 Thanks! Processing your document now...</div>', unsafe_allow_html=True)
    bird_speaks("Thanks! Processing your document now. Please wait")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    doc = fitz.open(pdf_path)
    text = " ".join([page.get_text() for page in doc])
    text = re.sub(r'\s+', ' ', text).strip()

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

    st.markdown(f"""
    <div class="bird-fly-3">
        <img src="{bird_img_url}" width="60"/>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="bird-message">🐦 Here is your output. Below is your summary.</div>', unsafe_allow_html=True)
    bird_speaks("Here is your output. Below is your summary")

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

    st.markdown('<div class="bird-message">🐦 Click the audio below to listen to the summary</div>', unsafe_allow_html=True)
    bird_speaks("Click the audio below to listen to the summary")

    try:
        tts = gTTS(paragraph[:3900], lang='en')
        audio_path = os.path.join(tempfile.gettempdir(), "output.mp3")
        tts.save(audio_path)
        with open(audio_path, "rb") as f:
            b64_audio = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <div class="audio-container">
            <audio controls>
                <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
            </audio>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error("❌ Audio generation failed.")
        st.exception(e)

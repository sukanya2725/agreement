import streamlit as st
import fitz  # PyMuPDF
import os
import re
from gtts import gTTS
import tempfile
import base64
import time
from rapidfuzz import fuzz
import textwrap

st.set_page_config(page_title="Agreement Analyzer", layout="centered")

# ✅ Your Duolingo bird GIF (uploaded to PostImage)
bird_gif = "https://i.postimg.cc/2jtSq2gC/duolingo-meme-flying-bird-kc0czqsh6zrv6aqv.gif"

# --- CSS for styling and bird animation ---
st.markdown(f"""
<style>
.bird {{
    position: absolute;
    width: 90px;
    z-index: 999;
}}
@keyframes fly {{
  0% {{ transform: translate(0px, 0px); opacity: 1; }}
  100% {{ transform: translate(200px, 100px); opacity: 0; }}
}}
.fly {{
    animation: fly 2s ease-in-out forwards;
}}

.bird-message {{
    margin-top: 140px;
    padding: 12px;
    background-color: #fff8dc;
    border-left: 5px solid orange;
    border-radius: 10px;
    font-weight: bold;
    color: #4e342e;
    animation: fadeIn 0.5s ease-in;
}}

@keyframes fadeIn {{
  0% {{ opacity: 0; }}
  100% {{ opacity: 1; }}
}}
</style>
""", unsafe_allow_html=True)

# --- Speak function ---
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

# --- Step-wise bird display + message + speak ---
def bird_fly_and_speak(message_text, speak_text):
    st.markdown(f"""
    <div class="bird fly">
        <img src="{bird_gif}" width="90">
    </div>
    """, unsafe_allow_html=True)
    speak(speak_text)
    st.markdown(f'<div class="bird-message">🐦 {message_text}</div>', unsafe_allow_html=True)
    time.sleep(2.5)

# --- Step 1: Upload instruction ---
bird_fly_and_speak("Step 1: Please upload your agreement file.", "Step one. Please upload your agreement file.")
uploaded_file = st.file_uploader("📤 Upload Agreement (PDF)", type=["pdf"])

if uploaded_file:
    # --- Step 2: Summary generation ---
    bird_fly_and_speak("Step 2: Processing your document, please wait...", "Step two. Processing your document.")

    # Save file temporarily
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

    # --- Step 3: Summary + Audio ---
    bird_fly_and_speak("Step 3: Here's your document summary below.", "Step three. Here is your document summary.")

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

    speak("Click the audio button to listen to the summary.")
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

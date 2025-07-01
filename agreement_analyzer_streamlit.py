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
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black

st.set_page_config(page_title="Agreement Analyzer", layout="centered")

# --- Enhanced Custom Styling ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    background-color: #fffde7;
}

h1, h2, h3 {
    font-weight: 600;
}

.block-container {
    padding: 2rem;
    animation: fadeInUp 0.8s ease-in-out;
}

@keyframes fadeInUp {
    0% { transform: translateY(20px); opacity: 0; }
    100% { transform: translateY(0); opacity: 1; }
}

@keyframes fadeInScale {
    0% { transform: scale(0.95); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
}

section[data-testid="stFileUploader"] > label {
    display: block;
    background: linear-gradient(to right, #fff8dc, #fff3b0);
    padding: 1.2rem;
    border-radius: 16px;
    border: 2px dashed #e6b800;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    margin-top: 1.5rem;
    transition: all 0.3s ease;
}

section[data-testid="stFileUploader"] > label:hover {
    background: #fff1a8;
    border-color: #cc9900;
    cursor: pointer;
}

.stButton > button {
    padding: 0.7em 1.6em;
    border-radius: 12px;
    font-weight: bold;
    border: none;
    color: white;
    animation: fadeInScale 0.5s ease-in-out;
    transition: all 0.3s ease-in-out;
    background: linear-gradient(135deg, #ff6f61, #ffb74d);
}

.stButton > button:hover {
    background: linear-gradient(135deg, #f4511e, #ffa726);
}

.flip-box {
  background-color: transparent;
  width: 100%;
  perspective: 1000px;
}

.flip-box-inner {
  position: relative;
  width: 100%;
  transition: transform 0.8s;
  transform-style: preserve-3d;
}

.flip-box:hover .flip-box-inner {
  transform: rotateY(180deg);
}

.flip-box-front, .flip-box-back {
  position: relative;
  width: 100%;
  backface-visibility: hidden;
  border-radius: 15px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  padding: 25px;
}

.flip-box-front {
  background-color: #fffde7;
  color: black;
}

.flip-box-back {
  background-color: #ffecb3;
  color: black;
  transform: rotateY(180deg);
}

[data-testid="stMarkdownContainer"] > div {
    animation: fadeInUp 0.7s ease;
}

.audio-container audio {
    width: 100%;
    border-radius: 10px;
    outline: none;
}

.bird-message {
    background: #f9f9f9;
    padding: 10px 20px;
    margin: 15px 0;
    border-left: 5px solid #ffb300;
    font-size: 1rem;
    font-weight: bold;
    border-radius: 8px;
    color: #4e342e;
    animation: fadeInUp 0.5s ease-in-out;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background-color:#003366;padding:15px;border-radius:10px">
<h1 style="color:white;text-align:center;">📄 Agreement Analyzer </h1>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="bird-message">🐦 Hi! Please upload your agreement PDF to begin analysis.</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("📤 Upload a PDF Agreement", type=["pdf"])
lang = st.selectbox("🌐 Select Output Language", ["English", "Marathi"])

if uploaded_file:
    st.markdown('<div class="bird-message">🐦 Thanks! Processing your document. Please wait...</div>', unsafe_allow_html=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    doc = fitz.open(pdf_path)
    text = " ".join([page.get_text() for page in doc])
    text = re.sub(r'\s+', ' ', text).strip()

    def smart_search(text, keywords, window=100):
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

    # Translation Section
    if lang == "Marathi":
        st.info("🌐 Translating to Marathi...")
        try:
            translated_paragraph = GoogleTranslator(source='auto', target='mr').translate(paragraph[:4000])
            translated_title = GoogleTranslator(source='auto', target='mr').translate(project_name)
            translated_parties = GoogleTranslator(source='auto', target='mr').translate(parties)
            translated_amount = GoogleTranslator(source='auto', target='mr').translate(amount)
            translated_scope = GoogleTranslator(source='auto', target='mr').translate(scope)
            translated_duration = GoogleTranslator(source='auto', target='mr').translate(duration)
        except Exception as e:
            st.error("❌ Marathi translation failed.")
            st.exception(e)
            translated_paragraph = paragraph
            translated_title = project_name
            translated_parties = parties
            translated_amount = amount
            translated_scope = scope
            translated_duration = duration

        final_text = translated_paragraph
        st.subheader("🈯 मराठी अनुवाद")
        st.markdown('<div class="bird-message">🐦 हे बघा, तुमचं मराठी सारांश तयार आहे!</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="flip-box">
          <div class="flip-box-inner">
            <div class="flip-box-front">
                <h3 style="color:#003366;">📝 मराठी सारांश पहा</h3>
                <p>Hover करा मराठी सारांश पाहण्यासाठी.</p>
            </div>
            <div class="flip-box-back">
                <h3 style="color:#003366;">📋 मराठी तपशील</h3>
                <p><b>📌 प्रकल्पाचे नाव:</b> {textwrap.fill(translated_title, 100)}</p>
                <p><b>📅 कराराची तारीख:</b> {date}</p>
                <p><b>👥 पक्ष:</b> {textwrap.fill(translated_parties, 100)}</p>
                <p><b>💰 रक्कम:</b> {textwrap.fill(translated_amount, 100)}</p>
                <p><b>📦 कामाचा व्याप:</b> {textwrap.fill(translated_scope, 100)}</p>
                <p><b>⏱ कालावधी:</b> {translated_duration}</p>
                <br><b>🧾 कायदेशीर अटी:</b><br>{"<br>".join(clause_results)}
                <br><br><b>🧠 सारांश परिच्छेद:</b><br>{textwrap.fill(translated_paragraph, 100)}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        final_text = paragraph
        st.markdown('<div class="bird-message">🐦 Here is your English summary below!</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="flip-box">
          <div class="flip-box-inner">
            <div class="flip-box-front">
                <h3 style="color:#003366;">📝 Tap to View Summary</h3>
                <p>Hover to reveal summary details.</p>
            </div>
            <div class="flip-box-back">
                <h3 style="color:#003366;">📋 Summary Details</h3>
                <p><b>📌 Project Name:</b> {textwrap.fill(project_name, 100)}</p>
                <p><b>📅 Agreement Date:</b> {date}</p>
                <p><b>👥 Parties Involved:</b> {textwrap.fill(parties, 100)}</p>
                <p><b>💰 Amount:</b> {textwrap.fill(amount, 100)}</p>
                <p><b>📦 Scope of Work:</b> {textwrap.fill(scope, 100)}</p>
                <p><b>⏱ Duration:</b> {duration}</p>
                <br><b>🧾 Legal Clauses:</b><br>{"<br>".join(clause_results)}
                <br><br><b>🧠 Summary Paragraph:</b><br>{textwrap.fill(paragraph, 100)}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Audio
    st.markdown('<div class="bird-message">🐦 Click below to hear the audio summary!</div>', unsafe_allow_html=True)
    st.subheader("🎧 Audio Summary")
    try:
        tts = gTTS(final_text[:3900], lang='mr' if lang == "Marathi" else 'en')
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

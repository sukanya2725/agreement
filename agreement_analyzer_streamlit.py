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

# Bird tracking state
if "bird_step" not in st.session_state:
    st.session_state.bird_step = 0
if "bird_said" not in st.session_state:
    st.session_state.bird_said = set()

# Bird speak

def bird_speak_once(voice_id, message):
    if voice_id not in st.session_state.bird_said:
        tts = gTTS(message, lang='en')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            with open(fp.name, "rb") as audio_file:
                b64 = base64.b64encode(audio_file.read()).decode()
                st.markdown(f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
                """, unsafe_allow_html=True)
        st.session_state.bird_said.add(voice_id)

# Bird position logic

def get_bird_position():
    if st.session_state.bird_step == 0:
        return "top: 20px; left: 30px;"
    elif st.session_state.bird_step == 1:
        return "top: 320px; left: 10px;"
    elif st.session_state.bird_step == 2:
        return "top: 1850px; left: 160px;"
    return "top: 30px; left: 30px;"

bird_gif = "https://i.postimg.cc/2jtSq2gC/duolingo-meme-flying-bird-kc0czqsh6zrv6aqv.gif"

st.markdown(f"""
<style>
.bird {{
    position: absolute;
    z-index: 999;
    width: 90px;
}}
</style>
<div class="bird" style="{get_bird_position()}">
    <img src="{bird_gif}" width="90">
</div>
""", unsafe_allow_html=True)

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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background-color:#003366;padding:15px;border-radius:10px">
<h1 style="color:white;text-align:center;">📄 Agreement Analyzer </h1>
</div>
""", unsafe_allow_html=True)

# --- Bird speaks step 1 ---
if st.session_state.bird_step == 0:
    bird_speak_once("welcome", "Welcome to my app")
    st.session_state.bird_step = 1

# File uploader step
uploaded_file = st.file_uploader("📤 Upload a PDF Agreement", type=["pdf"])
lang = st.selectbox("🌐 Select Output Language", ["English", "Marathi"])

if st.session_state.bird_step == 1:
    bird_speak_once("upload", "Upload your document here")

if uploaded_file:
    st.session_state.bird_step = 2
    bird_speak_once("summary", "Click below to listen to the summary. Thank you")

    # Audio Summary Output
    summary_text = "This is your audio summary sample text for testing."  # replace this later with real extracted summary
    st.subheader("🎧 Audio Summary")
    try:
        tts = gTTS(summary_text[:3900], lang='en')
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

import streamlit as st
import time
import base64
from gtts import gTTS
import tempfile

st.set_page_config(page_title="Flying Bird UI", layout="centered")

bird_gif = "https://cdn.pixabay.com/animation/2023/01/24/20/21/20-21-56-279_512.gif"

# --- CSS for animated bird ---
st.markdown(f"""
<style>
.bird {{
    position: absolute;
    width: 60px;
    z-index: 999;
    animation-duration: 2s;
    animation-fill-mode: forwards;
}}
@keyframes fly1 {{
  0% {{ transform: translate(0px, 0px); }}
  100% {{ transform: translate(150px, 20px); }}
}}
@keyframes fly2 {{
  0% {{ transform: translate(150px, 20px); }}
  100% {{ transform: translate(300px, 100px); }}
}}
@keyframes fly3 {{
  0% {{ transform: translate(300px, 100px); }}
  100% {{ transform: translate(450px, 160px); }}
}}
.fly-step-1 {{ animation-name: fly1; }}
.fly-step-2 {{ animation-name: fly2; animation-delay: 2s; }}
.fly-step-3 {{ animation-name: fly3; animation-delay: 4s; }}
.bird-message {{
    margin-top: 120px;
    padding: 10px;
    background-color: #fff8dc;
    border-left: 5px solid orange;
    border-radius: 8px;
    font-weight: bold;
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
    time.sleep(3)

# --- Step 1: Upload instruction ---
st.markdown(f'<div class="bird bird-img fly-step-1"><img src="{bird_gif}" width="60"></div>', unsafe_allow_html=True)
st.markdown('<div class="bird-message">🐦 Step 1: Please upload your agreement file.</div>', unsafe_allow_html=True)
speak("Step one. Please upload your agreement file.")

# Wait to simulate delay
time.sleep(2)

# --- Step 2: Summary instruction ---
st.markdown(f'<div class="bird bird-img fly-step-2"><img src="{bird_gif}" width="60"></div>', unsafe_allow_html=True)
st.markdown('<div class="bird-message">🐦 Step 2: Generating your document summary...</div>', unsafe_allow_html=True)
speak("Step two. Generating your document summary.")

# Wait
time.sleep(2)

# --- Step 3: Audio instruction ---
st.markdown(f'<div class="bird bird-img fly-step-3"><img src="{bird_gif}" width="60"></div>', unsafe_allow_html=True)
st.markdown('<div class="bird-message">🐦 Step 3: Click the button below to listen to the summary.</div>', unsafe_allow_html=True)
speak("Step three. Click the button to listen to the summary.")

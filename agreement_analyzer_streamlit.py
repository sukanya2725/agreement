import streamlit as st
import time
import base64
from gtts import gTTS
import tempfile

st.set_page_config(page_title="Flying Duolingo Bird Assistant", layout="centered")

# ✅ Your Duolingo flying bird GIF
bird_gif = "https://i.postimg.cc/2jtSq2gC/duolingo-meme-flying-bird-kc0czqsh6zrv6aqv.gif"

# --- CSS Animation + Bird Styles ---
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

# --- Bird speaks using gTTS ---
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

# --- Step Handler ---
def bird_fly_and_speak(step_text, instruction_text):
    st.markdown(f"""
    <div class="bird fly">
        <img src="{bird_gif}" width="90">
    </div>
    """, unsafe_allow_html=True)
    speak(instruction_text)
    st.markdown(f'<div class="bird-message">🐦 {step_text}</div>', unsafe_allow_html=True)
    time.sleep(2.5)  # wait for bird to disappear

# ✅ Step 1
bird_fly_and_speak("Step 1: Please upload your agreement file.", "Step one. Please upload your agreement file.")

# ✅ Step 2
bird_fly_and_speak("Step 2: Generating document summary.", "Step two. Generating your document summary.")

# ✅ Step 3
bird_fly_and_speak("Step 3: Click play to listen to the summary.", "Step three. Click the play button to listen.")

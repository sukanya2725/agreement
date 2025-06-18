# agreement_analyzer_streamlit.py

import streamlit as st
from pdf2image import convert_from_path
import pytesseract
from gtts import gTTS
import os
from deep_translator import GoogleTranslatorfrom PIL import Image
import tempfile
import base64

# Streamlit Title
st.title("📄 Agreement Analyzer with Translation and Audio")

# Upload PDF
uploaded_file = st.file_uploader("Upload a PDF Document", type=["pdf"])

# Language Selection
lang = st.selectbox("Select output language", ["English", "Marathi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    # Convert PDF to images
    pages = convert_from_path(pdf_path)

    extracted_text = ""
    st.info("🔍 Extracting text using OCR...")

    for page_num, page in enumerate(pages):
        text = pytesseract.image_to_string(page)
        extracted_text += f"\n\n--- Page {page_num+1} ---\n\n{text}"

    # Display Extracted Text
    st.subheader("📑 Extracted Text")
    st.text_area("OCR Output", extracted_text, height=300)

    # Translate if required
    if lang == "Marathi":
        st.info("🔄 Translating to Marathi...")
        translator = Translator()
        translated = GoogleTranslator(source='auto', target='mr').translate(text)
        final_text = translated.text
        st.subheader("🈯 Translated Text")
        st.text_area("Translated Output", final_text, height=300)
    else:
        final_text = extracted_text

    # Generate and play audio
    st.subheader("🔊 Listen to the Text")
    tts = gTTS(final_text, lang='mr' if lang == "Marathi" else 'en')
    audio_path = os.path.join(tempfile.gettempdir(), "output.mp3")
    tts.save(audio_path)

    # Load and embed audio player
    with open(audio_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
        b64 = base64.b64encode(audio_bytes).decode()
        audio_html = f"""
            <audio controls>
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                Your browser does not support the audio element.
            </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)

    st.success("✅ Done! You can listen or copy the output.")

import streamlit as st
import pytesseract
import fitz  # PyMuPDF
from gtts import gTTS
import os
from deep_translator import GoogleTranslator
import tempfile
import base64

st.set_page_config(page_title="Agreement Analyzer", layout="centered")
st.title("📄 Agreement Analyzer with Translation and Audio")

uploaded_file = st.file_uploader("Upload a PDF Document", type=["pdf"])
lang = st.selectbox("Select output language", ["English", "Marathi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    st.info("🔍 Extracting text from PDF...")
    try:
        doc = fitz.open(pdf_path)
        extracted_text = ""
        for page_num, page in enumerate(doc):
            text = page.get_text()
            extracted_text += f"\n\n--- Page {page_num+1} ---\n\n{text}"
    except Exception as e:
        st.error("❌ Failed to extract text from PDF.")
        st.exception(e)
        st.stop()

    st.subheader("📑 Extracted Text")
    st.text_area("OCR Output", extracted_text, height=300)

    if lang == "Marathi":
        st.info("🔄 Translating to Marathi...")
        try:
            translated = GoogleTranslator(source='auto', target='mr').translate(extracted_text)
        except Exception as e:
            st.error("❌ Marathi translation failed.")
            st.exception(e)
            translated = extracted_text
        final_text = translated
        st.subheader("🈯 Marathi Summary")
        st.text_area("Translated Output", final_text, height=300)
    else:
        final_text = extracted_text

    st.subheader("🔊 Listen to the Text")
    try:
        tts = gTTS(final_text, lang='mr' if lang == "Marathi" else 'en')
        audio_path = os.path.join(tempfile.gettempdir(), "output.mp3")
        tts.save(audio_path)
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
        st.success("✅ Audio generated successfully!")
    except Exception as e:
        st.error("❌ Failed to generate audio.")
        st.exception(e)

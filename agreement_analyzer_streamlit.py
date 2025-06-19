import streamlit as st
import fitz  # PyMuPDF
from gtts import gTTS
import os
from deep_translator import GoogleTranslator
import tempfile
import base64
import re

st.set_page_config(page_title="Agreement Analyzer", layout="centered")
st.title("📄 Agreement Analyzer with Translation and Audio")

uploaded_file = st.file_uploader("Upload a PDF Document", type=["pdf"])
lang = st.selectbox("Select output language", ["English", "Marathi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    st.info("🔍 Extracting and analyzing text from PDF...")
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
    except Exception as e:
        st.error("❌ Failed to extract text from PDF.")
        st.exception(e)
        st.stop()

    def extract_field(pattern):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else "Not found"

    title = extract_field(r"(?:title|subject|project name)[^\n:]*[:\-]?\s*(.+)")
    date = extract_field(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
    amount = extract_field(r"(?:Rs|₹)\s*([\d,]+)")
    parties = extract_field(r"between\s+(.*?)\s+and")
    duration = extract_field(r"within\s+(\d+.*?)\s")
    scope = extract_field(r"(scope of work.*?)\n")

    clauses = {
        "Confidentiality": "confidentiality",
        "Termination": "termination",
        "Dispute Resolution": "arbitration|dispute resolution",
        "Jurisdiction": "jurisdiction",
        "Force Majeure": "force majeure",
        "Signatures": "signed by|signature"
    }

    clause_results = []
    for name, keyword in clauses.items():
        clause_results.append(f"✅ {name}" if re.search(keyword, text, re.IGNORECASE) else f"❌ {name}")

    summary = f"""
📄 Agreement Summary:
- 📌 Title of Project: {title}
- 📅 Agreement Date: {date}
- 👥 Parties Involved: {parties}
- 💰 Amount: ₹{amount}
- 📦 Scope of Work: {scope}
- ⏱ Duration: {duration}

🧾 Legal Clauses:
{chr(10).join(clause_results)}
    """

    st.subheader("📑 Structured Summary")
    st.text_area("Summary", summary, height=300)

    if lang == "Marathi":
        st.info("🔄 Translating to Marathi...")
        try:
            final_text = GoogleTranslator(source='auto', target='mr').translate(summary)
        except Exception as e:
            st.error("❌ Marathi translation failed.")
            st.exception(e)
            final_text = summary
        st.subheader("🈯 Marathi Summary")
        st.text_area("Translated Output", final_text, height=300)
    else:
        final_text = summary

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

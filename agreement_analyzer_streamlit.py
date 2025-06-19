import streamlit as st
import pymupdf as fitz  # ✅ Safe and guaranteed to load PyMuPDF
from gtts import gTTS
import os
from deep_translator import GoogleTranslator
import tempfile
import base64
from rapidfuzz import fuzz

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

    def smart_search(text, keywords):
        lines = text.lower().split('\n')
        for line in lines:
            for keyword in keywords:
                if fuzz.partial_ratio(keyword.lower(), line.lower()) > 80:
                    return line.strip()
        return "Not found"

    title = smart_search(text, ["agreement", "title", "project name"])
    date = smart_search(text, ["date", "commencement date", "signed on", "agreement date"])
    amount = smart_search(text, ["rs", "amount", "total payment", "₹"])
    parties = smart_search(text, ["between", "by and between", "party a", "party b", "contractor"])
    duration = smart_search(text, ["within", "duration", "time period", "complete within", "calendar months"])
    scope = smart_search(text, ["scope", "scope of work", "services", "deliverables", "responsibilities"])

    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure", "nda"],
        "Termination": ["termination", "cancelled", "can be terminated", "terminate"],
        "Dispute Resolution": ["arbitration", "dispute", "resolved", "decision"],
        "Jurisdiction": ["jurisdiction", "governing law", "court"],
        "Force Majeure": ["force majeure", "act of god", "natural events", "unforeseen"],
        "Signatures": ["signed by", "signature", "authorized signatory"]
    }

    clause_results = []
    for name, keywords in clauses.items():
        found = smart_search(text, keywords)
        clause_results.append(f"✅ {name}" if found != "Not found" else f"❌ {name}")

    summary = f"""
📄 Agreement Summary:
📌 Title of Project – {title}
📅 Agreement Date – {date}
👥 Parties Involved – {parties}
💰 Amount – ₹{amount}
📦 Scope of Work – {scope}
⏱ Duration – {duration}

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

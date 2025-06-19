import streamlit as st
import pymupdf as fitz  # PyMuPDF
from gtts import gTTS
import os
from deep_translator import GoogleTranslator
import tempfile
import base64
from rapidfuzz import fuzz

st.set_page_config(page_title="Agreement Analyzer", layout="centered")
st.markdown("""
    <div style="background-color:#003366;padding:15px;border-radius:10px">
        <h1 style="color:white;text-align:center;">📄 Agreement Analyzer PRO</h1>
    </div>
    """, unsafe_allow_html=True)

uploaded_file = st.file_uploader("📤 Upload a PDF Agreement", type=["pdf"])
lang = st.selectbox("🌐 Select Output Language", ["English", "Marathi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("🔍 Extracting and analyzing text...")

    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
    except Exception as e:
        st.error("❌ Failed to extract text from PDF.")
        st.exception(e)
        st.stop()

    # 👇 Enhanced smart_search to scan entire text
    def smart_search(text, keywords):
        text = text.lower().replace('\n', ' ')
        best_score = 0
        best_match = "Not found"
        for keyword in keywords:
            for sentence in text.split('.'):
                score = fuzz.partial_ratio(keyword.lower(), sentence.strip())
                if score > best_score and score > 60:
                    best_score = score
                    best_match = sentence.strip()
        return best_match

    def safe(val):
        return val if val and val != "Not found" else "Not specified"

    # 🔎 Extract key fields with expanded keywords
    title = safe(smart_search(text, [
        "title", "project name", "agreement for", "subject", "work of", "construction of", "supply of"
    ]))
    date = safe(smart_search(text, [
        "agreement date", "this agreement is made", "dated", "commencement date", "signed on", "execution date"
    ]))
    amount = safe(smart_search(text, [
        "estimated cost", "₹", "rs", "contract value", "total amount", "amount payable"
    ]))
    parties = safe(smart_search(text, [
        "between", "by and between", "contractor", "municipal corporation", "party a", "party b"
    ]))
    duration = safe(smart_search(text, [
        "within", "duration", "calendar months", "complete within", "time frame"
    ]))
    scope = safe(smart_search(text, [
        "scope", "scope of work", "services include", "includes", "deliverables", "responsibilities"
    ]))

    # ✅ Clause detection
    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure", "nda"],
        "Termination": ["termination", "cancelled", "terminate"],
        "Dispute Resolution": ["arbitration", "dispute", "resolved", "decision of commissioner"],
        "Jurisdiction": ["jurisdiction", "governing law", "court", "legal"],
        "Force Majeure": ["force majeure", "natural events", "act of god", "unforeseen"],
        "Signatures": ["signed by", "signature", "authorized signatory"]
    }

    clause_results = []
    for name, keywords in clauses.items():
        found = smart_search(text, keywords)
        clause_results.append(f"✅ {name}" if found != "Not found" else f"❌ {name}")

    # 📑 Summary + Paragraph
    paragraph = f"This agreement"
    if parties != "Not specified":
        paragraph += f" is made between {parties}"
    if date != "Not specified":
        paragraph += f" on {date}"
    if scope != "Not specified":
        paragraph += f", covering work such as: {scope}"
    if amount != "Not specified":
        paragraph += f". The total value is ₹{amount}"
    if duration != "Not specified":
        paragraph += f", to be completed in {duration}."
    included = [c[2:] for c in clause_results if c.startswith("✅")]
    if included:
        paragraph += " It includes clauses like: " + ", ".join(included) + "."

    full_summary = f"""
📄 Agreement Summary:
📌 Title of Project – {title}
📅 Agreement Date – {date}
👥 Parties Involved – {parties}
💰 Amount – ₹{amount}
📦 Scope of Work – {scope}
⏱ Duration – {duration}

🧾 Legal Clauses:
{chr(10).join(clause_results)}

🧠 Summary Paragraph:
{paragraph}
"""

    st.markdown("""
        <div style='background-color:#f2f2f2;padding:20px;border-radius:10px'>
        <h4>🧾 Extracted Agreement Summary</h4>
    """, unsafe_allow_html=True)
    st.text_area("Summary Output", full_summary, height=350)
    st.markdown("</div>", unsafe_allow_html=True)

    # 🌐 Marathi Translation
    if lang == "Marathi":
        st.info("🌐 Translating to Marathi...")
        try:
            final_text = GoogleTranslator(source='auto', target='mr').translate(full_summary)
        except Exception as e:
            st.error("❌ Marathi translation failed.")
            st.exception(e)
            final_text = full_summary
        st.markdown("<h4>🈯 Marathi Translation</h4>", unsafe_allow_html=True)
        st.text_area("Translated Output", final_text, height=350)
    else:
        final_text = full_summary

    # 🎧 Text-to-Speech (Marathi or English)
    st.markdown("""
        <div style='background-color:#e0f7fa;padding:20px;border-radius:10px'>
        <h4>🔊 Audio Summary</h4>
    """, unsafe_allow_html=True)
    try:
        tts = gTTS(final_text, lang='mr' if lang == "Marathi" else 'en')
        audio_path = os.path.join(tempfile.gettempdir(), "output.mp3")
        tts.save(audio_path)

        with open(audio_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            b64 = base64.b64encode(audio_bytes).decode()
            audio_html = f"""
                <audio controls style='width:100%'>
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    Your browser does not support the audio element.
                </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
        st.success("✅ Audio generated successfully!")
    except Exception as e:
        st.error("❌ Failed to generate audio.")
        st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)

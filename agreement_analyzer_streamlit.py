import streamlit as st
import pymupdf as fitz # PyMuPDF
from gtts import gTTS
import os
import re
from deep_translator import GoogleTranslator
import tempfile
import base64
from rapidfuzz import fuzz
import textwrap

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

    def smart_search(text, keywords):
        text = text.lower().replace('\n', ' ')
        best_score = 0
        best_match = "Not specified"
        for keyword in keywords:
            for sentence in text.split('.'):
                score = fuzz.partial_ratio(keyword.lower(), sentence.strip())
                if score > best_score and score > 60:
                    best_score = score
                    best_match = sentence.strip()
        return best_match

    # Field Extraction
    title_match = re.search(r'(project\s*(name|title)|subject|work of|name of work)[:\-]?\s*(.*?)(\.|\n|$)', text, re.IGNORECASE)
    title = title_match.group(3).strip() if title_match else smart_search(text, ["project", "work of", "tender"])

    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    date = date_match.group(0) if date_match else "Not specified"

    amount_match = re.search(r'(₹|rs\.?)\s*([\d,]+)', text.lower())
    amount = f"₹{amount_match.group(2)}" if amount_match else "Not specified"

    parties_match = re.search(r'(between.*?solapur municipal.*?commissioner.*?smc.*?)\n', text, re.IGNORECASE | re.DOTALL)
    parties = parties_match.group(1).strip().replace('\n', ' ') if parties_match else smart_search(text, ["contractor", "between", "municipal", "company"])

    scope = smart_search(text, ["scope of work", "the work includes", "responsibility", "project includes"])

    duration_match = re.search(r'(within\s+\d+\s+(calendar\s+)?months)', text.lower())
    duration = duration_match.group(1) if duration_match else smart_search(text, ["completion", "calendar months", "time period"])

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
        clause_results.append(f"✅ {name}" if found != "Not specified" else f"❌ {name}")

    # Paragraph Summary
    paragraph = f"This agreement"
    if parties != "Not specified":
        paragraph += f" is made between {parties}"
    if date != "Not specified":
        paragraph += f" on {date}"
    if scope != "Not specified":
        paragraph += f", covering work such as: {scope}"
    if amount != "Not specified":
        paragraph += f". The total contract value is {amount}"
    if duration != "Not specified":
        paragraph += f", expected to be completed {duration}."
    included = [c[2:] for c in clause_results if c.startswith("✅")]
    if included:
        paragraph += " It includes clauses like: " + ", ".join(included) + "."

    # Display Summary
    st.subheader("📑 Extracted Summary")
    st.markdown(f"""
    <div style="font-size:17px; background:#f4f6f8; padding:15px; border-radius:10px">
    <p><b>📌 Title of Project:</b> {textwrap.fill(title, 100) if title else "Not specified"}</p>
    <p><b>📅 Agreement Date:</b> {date}</p>
    <p><b>👥 Parties Involved:</b> {textwrap.fill(parties, 100)}</p>
    <p><b>💰 Amount:</b> {amount}</p>
    <p><b>📦 Scope of Work:</b> {textwrap.fill(scope, 100)}</p>
    <p><b>⏱ Duration:</b> {duration}</p>
    <br><b>🧾 Legal Clauses:</b><br>
    {"<br>".join(clause_results)}
    <br><br><b>🧠 Summary Paragraph:</b><br>
    {textwrap.fill(paragraph, 100)}
    </div>
    """, unsafe_allow_html=True)

    # Translation
    if lang == "Marathi":
        st.info("🌐 Translating to Marathi...")
        try:
            translated = GoogleTranslator(source='auto', target='mr').translate(paragraph)
        except Exception as e:
            st.error("❌ Marathi translation failed.")
            st.exception(e)
            translated = paragraph
        final_text = translated
        st.subheader("🈯 Marathi Translation")
        st.text_area("Translated Output", final_text, height=300)
    else:
        final_text = paragraph

    # Audio
    st.subheader("🎧 Audio Summary")
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

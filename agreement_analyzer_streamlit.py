import streamlit as st
import pymupdf as fitz
from gtts import gTTS
import os
import re
from deep_translator import GoogleTranslator
import tempfile
import base64
from rapidfuzz import fuzz
import textwrap
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

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
        all_text = []
        total_pages = len(doc)
        progress_bar = st.progress(0)

        for i, page in enumerate(doc):
            page_text = page.get_text().replace('\n', ' ').strip()
            all_text.append(page_text)
            progress_bar.progress((i + 1) / total_pages)

        text = " ".join(all_text)
        text = re.sub(r'\s+', ' ', text).strip()
        progress_bar.empty()

    except Exception as e:
        st.error("❌ Failed to extract text from PDF.")
        st.exception(e)
        st.stop()

    def smart_search(text_content, keywords, search_window=100):
        best_score = 0
        best_match = "Not specified"
        segments = re.split(r'(?<=[.!?])\s+|\n{2,}', text_content)
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for segment in segments:
                segment_lower = segment.strip().lower()
                if keyword_lower in segment_lower:
                    score = 100
                else:
                    score = fuzz.partial_ratio(keyword_lower, segment_lower)
                if score > best_score and score >= 70:
                    best_score = score
                    match_start = segment_lower.find(keyword_lower)
                    if match_start != -1:
                        context_start = max(0, match_start - 30)
                        context_end = min(len(segment), match_start + len(keyword) + search_window)
                        best_match = segment[context_start:context_end].strip()
                    else:
                        best_match = segment.strip()
        return best_match

    project_name = smart_search(text, ["project title", "name of work", "tender for"])
    scope = smart_search(text, ["scope of work", "nature of work", "work includes"])
    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    date = date_match.group(0) if date_match else "Not specified"
    amount = smart_search(text, ["contract value", "estimated cost", "rupees"])
    parties = smart_search(text, ["between", "municipal corporation", "contractor"])
    duration = smart_search(text, ["within", "completion period", "construction time"])

    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure"],
        "Termination": ["termination", "terminate"],
        "Dispute Resolution": ["arbitration", "dispute"],
        "Jurisdiction": ["jurisdiction", "court"],
        "Force Majeure": ["force majeure", "natural events"],
        "Signatures": ["signed by", "signature"]
    }

    clause_results = []
    for name, keywords in clauses.items():
        found = smart_search(text, keywords)
        clause_results.append(f"✅ {name}" if found != "Not specified" else f"❌ {name}")

    paragraph = f"This agreement is made between {parties} on {date} for the project: {project_name}, covering: {scope}. Contract value: {amount}, Duration: {duration}."
    included = [c[2:] for c in clause_results if c.startswith("✅")]
    if included:
        paragraph += " Clauses included: " + ", ".join(included) + "."

    st.subheader("📑 Extracted Summary")
    st.markdown(f"""
    <div style="font-size:17px; background:#f4f6f8; padding:15px; border-radius:10px">
    <p><b>📌 Project Name:</b> {textwrap.fill(project_name, 100)}</p>
    <p><b>📅 Agreement Date:</b> {date}</p>
    <p><b>👥 Parties Involved:</b> {textwrap.fill(parties, 100)}</p>
    <p><b>💰 Amount:</b> {textwrap.fill(amount, 100)}</p>
    <p><b>📦 Scope of Work:</b> {textwrap.fill(scope, 100)}</p>
    <p><b>⏱ Duration:</b> {duration}</p>
    <br><b>🧾 Legal Clauses:</b><br>{"<br>".join(clause_results)}
    <br><br><b>🧠 Summary Paragraph:</b><br>{textwrap.fill(paragraph, 100)}
    </div>
    """, unsafe_allow_html=True)

    # Translation
    if lang == "Marathi":
        st.info("🌐 Translating to Marathi...")
        try:
            translated = GoogleTranslator(source='auto', target='mr').translate(paragraph[:4000])
        except Exception as e:
            st.error("❌ Marathi translation failed.")
            st.exception(e)
            translated = paragraph
        final_text = translated
        st.subheader("🈯 Marathi Translation")
        st.text_area("Translated Output", final_text, height=300)
    else:
        final_text = paragraph

    # Audio Summary
    st.subheader("🎧 Audio Summary")
    try:
        tts = gTTS(final_text[:3900], lang='mr' if lang == "Marathi" else 'en')
        audio_path = os.path.join(tempfile.gettempdir(), "output.mp3")
        tts.save(audio_path)
        with open(audio_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            b64 = base64.b64encode(audio_bytes).decode()
            st.markdown(f"""
                <audio controls style='width:100%'>
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    Your browser does not support the audio element.
                </audio>
            """, unsafe_allow_html=True)
        st.success("✅ Audio generated successfully!")
    except Exception as e:
        st.error("❌ Failed to generate audio.")
        st.exception(e)

    # Downloadable PDF Summary
    st.subheader("📥 Download PDF Summary")
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica", 12)
    margin = 50
    y = height - margin

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Agreement Summary")
    y -= 30

    for line in textwrap.wrap(paragraph, 100):
        if y < margin:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = height - margin
        c.drawString(margin, y, line)
        y -= 20

    c.save()
    buffer.seek(0)

    b64_pdf = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="agreement_summary.pdf">📥 Download PDF</a>'
    st.markdown(href, unsafe_allow_html=True)

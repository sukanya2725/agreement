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
from reportlab.lib.units import inch
from reportlab.lib.colors import black

# ✅ No need to use st.set_option for upload size
# Set maxUploadSize = 1000 in .streamlit/config.toml

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

        if total_pages > 1000:
            st.warning(f"⚠ This PDF has {total_pages} pages. Processing may be slow.")

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
                        extracted_snippet = segment[context_start:context_end].strip()
                        best_match = extracted_snippet
                    else:
                        best_match = segment.strip()
        return best_match

    project_name = smart_search(text, ["project title", "name of work", "tender for"], 150)
    scope = smart_search(text, ["scope of work", "work includes", "nature of work"], 250)
    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    date = date_match.group(0) if date_match else "Not specified"

    amount_sentence = smart_search(text, ["contract value", "rupees", "estimated cost"], 100)
    amount_match = re.search(r'(?:Rs\.?|₹)?\s*[\d,]+(?:\.\d{1,2})?', amount_sentence)
    amount = amount_match.group(0) if amount_match else amount_sentence

    parties = smart_search(text, ["between", "municipal corporation", "contractor"])
    duration = smart_search(text, ["calendar months", "project completion time", "within"])

    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure"],
        "Termination": ["termination", "terminate"],
        "Dispute Resolution": ["arbitration", "dispute"],
        "Jurisdiction": ["jurisdiction", "court"],
        "Force Majeure": ["force majeure", "act of god"],
        "Signatures": ["signed by", "signature"]
    }

    clause_results = []
    for name, keys in clauses.items():
        result = smart_search(text, keys)
        clause_results.append(f"✅ {name}" if result != "Not specified" else f"❌ {name}")

    paragraph = "This agreement"
    if parties != "Not specified":
        paragraph += f" is made between {parties}"
    if date != "Not specified":
        paragraph += f" on {date}"
    if project_name != "Not specified":
        paragraph += f" for the project: {project_name}"
    if scope != "Not specified":
        paragraph += f", covering: {scope}"
    if amount != "Not specified":
        paragraph += f". The contract value is {amount}"
    if duration != "Not specified":
        paragraph += f", with a duration of {duration}."
    if any(c.startswith("✅") for c in clause_results):
        paragraph += " Clauses include: " + ", ".join([c[2:] for c in clause_results if c.startswith("✅")]) + "."

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

    st.subheader("🎧 Audio Summary")
    try:
        max_chars = 3900
        trimmed_text = final_text[:max_chars] + "..." if len(final_text) > max_chars else final_text
        tts = gTTS(trimmed_text, lang='mr' if lang == "Marathi" else 'en')
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

    # PDF DOWNLOAD WITH BORDER
    summary_pdf_path = os.path.join(tempfile.gettempdir(), "agreement_summary_with_border.pdf")
    c = canvas.Canvas(summary_pdf_path, pagesize=A4)
    width, height = A4

    c.setLineWidth(2)
    c.setStrokeColor(black)
    c.rect(inch / 2, inch / 2, width - inch, height - inch)

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 80, f"Project Title: {project_name}")

    c.setFont("Helvetica", 12)
    y = height - 120
    for line in textwrap.wrap(paragraph, width=95):
        c.drawString(inch, y, line)
        y -= 16
        if y < inch:
            c.showPage()
            c.setLineWidth(2)
            c.setStrokeColor(black)
            c.rect(inch / 2, inch / 2, width - inch, height - inch)
            y = height - inch

    c.save()

    with open(summary_pdf_path, "rb") as f:
        b64_pdf = base64.b64encode(f.read()).decode()
        download_link = f'<a href="data:application/pdf;base64,{b64_pdf}" download="agreement_summary.pdf">📥 Download Summary PDF with Border</a>'
        st.markdown(download_link, unsafe_allow_html=True)

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

st.set_page_config(page_title="Agreement Analyzer PRO", layout="centered")

# --- Custom CSS Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
        background-color: #f4f6f8;
    }

    .main-title {
        background-color: #003366;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 20px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }

    .card {
        background-color: #ffffff;
        padding: 15px 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0px 3px 6px rgba(0,0,0,0.05);
    }

    .card-title {
        color: #003366;
        font-weight: bold;
        font-size: 18px;
        margin-bottom: 5px;
    }

    .summary-box {
        background: #e6f0ff;
        padding: 15px;
        border-radius: 10px;
        font-size: 16px;
        margin-top: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .download-link a {
        background-color: #003366;
        color: white !important;
        padding: 10px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        display: inline-block;
        transition: 0.3s ease;
    }

    .download-link a:hover {
        background-color: #002244;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><h1>📄 Agreement Analyzer PRO</h1></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("📤 Upload a PDF Agreement", type=["pdf"])
lang = st.selectbox("🌐 Select Output Language", ["English", "Marathi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    st.info("🔍 Extracting and analyzing text...")

    try:
        doc = fitz.open(pdf_path)
        all_text = []
        total_pages = len(doc)

        if total_pages > 1000:
            st.warning(f"⚠️ This PDF has {total_pages} pages. Processing may be slow.")

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
        if result != "Not specified":
            clause_results.append(f"📌 <b>{name}</b>: {result}")
        else:
            clause_results.append(f"❌ <b>{name}</b>: Not found")

    paragraph = "This agreement"
    if parties != "Not specified": paragraph += f" is made between {parties}"
    if date != "Not specified": paragraph += f" on {date}"
    if project_name != "Not specified": paragraph += f" for the project: {project_name}"
    if scope != "Not specified": paragraph += f", covering: {scope}"
    if amount != "Not specified": paragraph += f". The contract value is {amount}"
    if duration != "Not specified": paragraph += f", with a duration of {duration}."
    if clause_results: paragraph += "\n\nKey Clauses:\n" + "\n".join(re.sub('<.*?>', '', c) for c in clause_results)

    st.markdown(f'<div class="card summary-box"><div class="card-title">🧠 Summary Paragraph</div>{paragraph}</div>', unsafe_allow_html=True)

    for clause in clause_results:
        st.markdown(f'<div class="card">{clause}</div>', unsafe_allow_html=True)

    pdf_path = os.path.join(tempfile.gettempdir(), "styled_summary.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    c.setLineWidth(2)
    c.setStrokeColor(black)
    c.rect(inch / 2, inch / 2, width - inch, height - inch)

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 80, f"Project Title: {project_name}")

    c.setFont("Helvetica-Bold", 14)
    y = height - 120
    fields = [
        ("Agreement Date", date),
        ("Parties Involved", parties),
        ("Amount", amount),
        ("Scope of Work", scope),
        ("Duration", duration),
    ]

    for label, content in fields:
        c.drawString(inch, y, f"{label}:")
        y -= 16
        for line in textwrap.wrap(content, width=95):
            c.setFont("Helvetica", 12)
            c.drawString(inch + 20, y, line)
            y -= 14
        y -= 10
        if y < inch:
            c.showPage()
            c.setLineWidth(2)
            c.setStrokeColor(black)
            c.rect(inch / 2, inch / 2, width - inch, height - inch)
            y = height - inch

    c.setFont("Helvetica-Bold", 14)
    c.drawString(inch, y, "Key Clauses:")
    y -= 16
    for clause in clause_results:
        clause_clean = re.sub('<.*?>', '', clause)
        for line in textwrap.wrap(clause_clean, width=95):
            c.setFont("Helvetica", 12)
            c.drawString(inch + 20, y, line)
            y -= 14
        y -= 8
        if y < inch:
            c.showPage()
            c.setLineWidth(2)
            c.setStrokeColor(black)
            c.rect(inch / 2, inch / 2, width - inch, height - inch)
            y = height - inch

    c.save()

    with open(pdf_path, "rb") as f:
        b64_pdf = base64.b64encode(f.read()).decode()
        st.markdown(f'<div class="download-link"><a href="data:application/pdf;base64,{b64_pdf}" download="styled_summary.pdf">📥 Download Summary PDF with Border</a></div>', unsafe_allow_html=True)

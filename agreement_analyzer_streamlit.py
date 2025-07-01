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

# --- Main Heading ---
st.markdown('<div class="main-title"><h1>📄 Agreement Analyzer PRO</h1></div>', unsafe_allow_html=True)

# --- File Upload ---
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
                        best_match = segment[context_start:context_end].strip()
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
    clause_results = [f"✅ {name}" if smart_search(text, keys) != "Not specified" else f"❌ {name}" for name, keys in clauses.items()]

    paragraph = "This agreement"
    if parties != "Not specified": paragraph += f" is made between {parties}"
    if date != "Not specified": paragraph += f" on {date}"
    if project_name != "Not specified": paragraph += f" for the project: {project_name}"
    if scope != "Not specified": paragraph += f", covering: {scope}"
    if amount != "Not specified": paragraph += f". The contract value is {amount}"
    if duration != "Not specified": paragraph += f", with a duration of {duration}."
    included_clauses = [c[2:] for c in clause_results if c.startswith("✅")]
    if included_clauses: paragraph += " Clauses include: " + ", ".join(included_clauses) + "."

    # --- Output Cards ---
    st.markdown(f'<div class="card"><div class="card-title">📌 Project Name</div>{project_name}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><div class="card-title">📅 Agreement Date</div>{date}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><div class="card-title">👥 Parties Involved</div>{parties}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><div class="card-title">💰 Amount</div>{amount}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><div class="card-title">📦 Scope of Work</div>{scope}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><div class="card-title">⏱ Duration</div>{duration}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card"><div class="card-title">🧾 Legal Clauses</div>{"<br>".join(clause_results)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card summary-box"><div class="card-title">🧠 Summary Paragraph</div>{paragraph}</div>', unsafe_allow_html=True)

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

    # --- Audio ---
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

    # --- Download PDF Summary ---
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf_download_path = os.path.join(tempfile.gettempdir(), "agreement_summary.pdf")
    c = canvas.Canvas(pdf_download_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(100, height - 100, "Project Title: " + project_name)
    c.setFont("Helvetica", 12)
    y = height - 150
    for line in textwrap.wrap(paragraph, width=100):
        c.drawString(50, y, line)
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()

    with open(pdf_download_path, "rb") as f:
        pdf_bytes = f.read()
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="agreement_summary.pdf">📥 Download PDF Summary</a>'
        st.markdown(f'<div class="download-link">{href}</div>', unsafe_allow_html=True)

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
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Increase file upload limit to 1000 MB
st.set_option('server.maxUploadSize', 1000)

# PDF styling function
def create_styled_summary_pdf(summary_text, filename="agreement_summary.pdf"):
    file_path = os.path.join(tempfile.gettempdir(), filename)
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleN.fontSize = 11
    styleN.leading = 14

    margin_left = 1 * inch
    margin_right = width - 1 * inch
    margin_top = height - 1 * inch
    margin_bottom = 1 * inch

    lines = summary_text.split('\n')
    text_chunks = []
    temp_chunk = ""
    for line in lines:
        if len(temp_chunk) + len(line) < 600:
            temp_chunk += line + "\n"
        else:
            text_chunks.append(temp_chunk.strip())
            temp_chunk = line + "\n"
    if temp_chunk:
        text_chunks.append(temp_chunk.strip())

    for chunk in text_chunks:
        c.setStrokeColor(colors.HexColor("#003366"))
        c.setFillColor(colors.HexColor("#003366"))
        c.setLineWidth(4)
        c.rect(0.5 * inch, 0.5 * inch, width - inch, height - inch)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1 * inch, height - 0.75 * inch, "\ud83d\udcc4 Agreement Summary Report")

        f = Frame(margin_left, margin_bottom, width - 2 * inch, height - 2 * inch - 0.3 * inch, showBoundary=0)
        para = Paragraph(chunk.replace('\n', '<br />'), styleN)
        f.addFromList([para], c)

        c.showPage()

    c.save()
    return file_path

# Streamlit UI
st.set_page_config(page_title="Agreement Analyzer", layout="centered")
st.markdown("""
<div style="background-color:#003366;padding:15px;border-radius:10px">
<h1 style="color:white;text-align:center;">\ud83d\udcc4 Agreement Analyzer PRO</h1>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("\ud83d\udcc4 Upload a PDF Agreement", type=["pdf"])
lang = st.selectbox("\ud83c\udf10 Select Output Language", ["English", "Marathi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("\ud83d\udd0d Extracting and analyzing text...")

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
        st.error("\u274c Failed to extract text from PDF.")
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
                score = 100 if keyword_lower in segment_lower else fuzz.partial_ratio(keyword_lower, segment_lower)
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

    project_name = smart_search(text, ["project title", "name of work", "subject", "tender for"])
    scope = smart_search(text, ["scope of work", "the work consists of", "nature of work", "description of work"])
    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    date = date_match.group(0) if date_match else "Not specified"
    amount = smart_search(text, ["contract value", "final payable amount", "estimated cost", "rupees"])
    parties = smart_search(text, ["between", "municipal corporation", "contractor", "agreement signed"])
    duration = smart_search(text, ["within", "calendar months", "construction period"])

    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure"],
        "Termination": ["termination", "cancelled"],
        "Dispute Resolution": ["arbitration", "dispute"],
        "Jurisdiction": ["jurisdiction", "court"],
        "Force Majeure": ["force majeure", "act of god"],
        "Signatures": ["signed by", "signature"]
    }

    clause_results = [
        f"\u2705 {name}" if smart_search(text, keywords) != "Not specified" else f"\u274c {name}"
        for name, keywords in clauses.items()
    ]

    paragraph = f"This agreement is made between {parties} on {date} for the project: {project_name}, covering work such as: {scope}. The contract value is: {amount}, with a total project duration of {duration}."
    included = [c[2:] for c in clause_results if c.startswith("\u2705")]
    if included:
        paragraph += " The agreement includes clauses like: " + ", ".join(included) + "."

    st.subheader("\ud83d\udcc1 Extracted Summary")
    st.markdown(f"""
    <div style="font-size:17px; background:#f4f6f8; padding:15px; border-radius:10px">
    <p><b>\ud83d\udccc Project Name:</b> {textwrap.fill(project_name, 100)}</p>
    <p><b>\ud83d\uddd3 Agreement Date:</b> {date}</p>
    <p><b>\ud83d\udc65 Parties Involved:</b> {textwrap.fill(parties, 100)}</p>
    <p><b>\ud83d\udcb0 Amount:</b> {textwrap.fill(amount, 100)}</p>
    <p><b>\ud83d\udce6 Scope of Work:</b> {textwrap.fill(scope, 100)}</p>
    <p><b>\u23f1 Duration:</b> {duration}</p>
    <br><b>\ud83d\uddfe Legal Clauses:</b><br>{"<br>".join(clause_results)}
    <br><br><b>\ud83e\udde0 Summary Paragraph:</b><br>{textwrap.fill(paragraph, 100)}
    </div>
    """, unsafe_allow_html=True)

    final_text = paragraph
    if lang == "Marathi":
        st.info("\ud83c\udf10 Translating to Marathi...")
        try:
            final_text = GoogleTranslator(source='auto', target='mr').translate(paragraph[:4000])
        except Exception as e:
            st.error("\u274c Marathi translation failed.")
            st.exception(e)

    # Audio
    st.subheader("\ud83c\udfb5 Audio Summary")
    try:
        trimmed_text = final_text[:3900] + "..." if len(final_text) > 3900 else final_text
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
        st.success("\u2705 Audio generated successfully!")
    except Exception as e:
        st.error("\u274c Failed to generate audio.")
        st.exception(e)

    # PDF Download
    styled_pdf_path = create_styled_summary_pdf(final_text)
    with open(styled_pdf_path, "rb") as f:
        st.download_button(
            label="\ud83d\udcc5 Download Styled PDF Summary",
            data=f,
            file_name="agreement_summary.pdf",
            mime="application/pdf"
        )

# Your updated Streamlit Agreement Analyzer full code
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

st.set_page_config(page_title="Agreement Analyzer", layout="centered")

# --- Custom Styling with Animation and Bird ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    background-color: #fffde7;
}

.sticky-header {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    background: linear-gradient(to right, #003366, #004d66);
    color: white;
    padding: 12px 20px;
    z-index: 1000;
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.bird-animation {
    position: fixed;
    bottom: 10px;
    right: 10px;
    width: 80px;
    height: 80px;
    background-image: url('https://i.postimg.cc/W3rZnqJy/duobird.gif');
    background-size: cover;
    animation: float 2s ease-in-out infinite;
}

@keyframes float {
    0% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
    100% { transform: translateY(0); }
}

section[data-testid="stFileUploader"] > label {
    background: linear-gradient(to right, #fff8dc, #fff3b0);
    padding: 1.2rem;
    border-radius: 16px;
    border: 2px dashed #e6b800;
    text-align: center;
    margin-top: 1.5rem;
}

.stButton > button {
    padding: 0.7em 1.6em;
    border-radius: 12px;
    font-weight: bold;
    border: none;
    color: white;
    background: linear-gradient(135deg, #ff6f61, #ffb74d);
    transition: 0.3s ease;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #f4511e, #ffa726);
}

.marathi-box {
    background-color: #fff9c4;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="sticky-header">📄 Agreement Analyzer</div>
<div class="bird-animation"></div>
<br><br><br>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📤 Upload a PDF Agreement", type=["pdf"])
lang = st.selectbox("🌐 Select Output Language", ["English", "Marathi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    doc = fitz.open(pdf_path)
    text = " ".join([page.get_text() for page in doc])
    text = re.sub(r'\s+', ' ', text).strip()

    def smart_search(text, keywords, window=100):
        best = "Not specified"
        score = 0
        segments = re.split(r'(?<=[.!?])\s+', text)
        for keyword in keywords:
            for segment in segments:
                s = fuzz.partial_ratio(keyword.lower(), segment.lower())
                if s > score and s > 70:
                    score = s
                    best = segment
        return best

    project = smart_search(text, ["project title", "name of work", "tender for"])
    scope = smart_search(text, ["scope of work", "work includes"])
    date = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    date = date.group(0) if date else "Not specified"
    amt = smart_search(text, ["contract value", "estimated cost"])
    amt_val = re.search(r'(?:Rs\.?|₹)?\s*[\d,]+(?:\.\d{1,2})?', amt)
    amt = amt_val.group(0) if amt_val else amt
    parties = smart_search(text, ["between", "municipal corporation", "contractor"])
    duration = smart_search(text, ["calendar months", "completion time", "within"])

    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure"],
        "Termination": ["termination", "terminate"],
        "Dispute Resolution": ["arbitration", "dispute"],
        "Jurisdiction": ["jurisdiction", "court"],
        "Force Majeure": ["force majeure"],
        "Signatures": ["signed by", "signature"]
    }

    clause_results = [f"✅ {k}" if smart_search(text, v) != "Not specified" else f"❌ {k}" for k, v in clauses.items()]

    paragraph = f"This agreement"
    if parties != "Not specified": paragraph += f" is made between {parties}"
    if date != "Not specified": paragraph += f" on {date}"
    if project != "Not specified": paragraph += f" for the project: {project}"
    if scope != "Not specified": paragraph += f", covering: {scope}"
    if amt != "Not specified": paragraph += f". The contract value is {amt}"
    if duration != "Not specified": paragraph += f", with a duration of {duration}."
    if any(c.startswith("✅") for c in clause_results):
        paragraph += " Clauses include: " + ", ".join([c[2:] for c in clause_results if c.startswith("✅")]) + "."

    if lang == "Marathi":
        st.markdown("<div class='marathi-box'>", unsafe_allow_html=True)
        try:
            final_text = GoogleTranslator(source='auto', target='mr').translate(paragraph[:4000])
        except:
            final_text = paragraph
        st.subheader("🈯 मराठी सारांश")
        st.text_area("Marathi Summary", final_text, height=300)
        st.markdown("</div>", unsafe_allow_html=True)

        # Marathi PDF
        summary_pdf_path = os.path.join(tempfile.gettempdir(), "marathi_summary.pdf")
        c = canvas.Canvas(summary_pdf_path, pagesize=A4)
        c.setFont("Helvetica", 12)
        y = 800
        for line in textwrap.wrap(final_text, width=95):
            c.drawString(50, y, line)
            y -= 16
            if y < 50:
                c.showPage()
                c.setFont("Helvetica", 12)
                y = 800
        c.save()
        with open(summary_pdf_path, "rb") as f:
            b64_pdf = base64.b64encode(f.read()).decode()
            st.markdown(f'<a href="data:application/pdf;base64,{b64_pdf}" download="marathi_summary.pdf">📥 Download Marathi Summary PDF</a>', unsafe_allow_html=True)
    else:
        final_text = paragraph
        st.subheader("📝 English Summary")
        st.text_area("Summary", final_text, height=300)

    # Audio
    tts = gTTS(final_text[:3900], lang='mr' if lang == "Marathi" else 'en')
    audio_path = os.path.join(tempfile.gettempdir(), "output.mp3")
    tts.save(audio_path)
    with open(audio_path, "rb") as f:
        b64_audio = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <div class="fixed-audio">
        <audio controls>
            <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
        </audio>
    </div>
    """, unsafe_allow_html=True)

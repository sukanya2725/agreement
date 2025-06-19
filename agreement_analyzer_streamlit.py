import streamlit as st
import pymupdf as fitz
from gtts import gTTS
import os
from deep_translator import GoogleTranslator
import tempfile
import base64
from rapidfuzz import fuzz

# Page config
st.set_page_config(page_title="Agreement Analyzer", layout="centered")

# Title with style
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
        lines = text.lower().split('\n')
        best_score = 0
        best_line = "Not found"
        for line in lines:
            for keyword in keywords:
                score = fuzz.partial_ratio(keyword.lower(), line.lower())
                if score > best_score and score > 60:
                    best_score = score
                    best_line = line.strip()
        return best_line

    def safe(val):
        return val if val and val != "Not found" else "Not specified"

    # Key fields
    title = safe(smart_search(text, ["title", "project name", "agreement for", "subject"]))
    date = safe(smart_search(text, ["date", "commencement", "signed on", "agreement date"]))
    amount = safe(smart_search(text, ["rs", "amount", "contract value", "₹", "cost"]))
    parties = safe(smart_search(text, ["between", "by and between", "contractor", "company"]))
    duration = safe(smart_search(text, ["within", "duration", "calendar months", "complete within"]))
    scope = safe(smart_search(text, ["scope", "work includes", "responsibilities", "services"]))

    # Clause checklist
    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure", "nda"],
        "Termination": ["termination", "cancelled", "terminate"],
        "Dispute Resolution": ["arbitration", "dispute", "resolved"],
        "Jurisdiction": ["jurisdiction", "governing law", "court"],
        "Force Majeure": ["force majeure", "natural events", "unforeseen"],
        "Signatures": ["signed by", "signature", "authorized signatory"]
    }

    clause_results = []
    for name, keywords in clauses.items():
        found = smart_search(text, keywords)
        clause_results.append(f"✅ {name}" if found != "Not found" else f"❌ {name}")

    # Build summary
    paragraph = f"""
This agreement{' between ' + parties if parties != 'Not specified' else ''}{' on ' + date if date != 'Not specified' else ''}, 
covers {scope if scope != 'Not specified' else 'a set of defined work'}. 
The total amount is ₹{amount if amount != 'Not specified' else 'N/A'} and is expected to be completed in {duration}.
"""
    included = [c[2:] for c in clause_results if c.startswith("✅")]
    if included:
        paragraph += " Clauses included: " + ", ".join(included) + "."

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

    # Styled summary display
    st.markdown("""
        <div style='background-color:#f2f2f2;padding:20px;border-radius:10px'>
        <h4>🧾 Extracted Agreement Summary</h4>
    """, unsafe_allow_html=True)
    st.text_area("Summary Output", full_summary, height=350)
    st.markdown("</div>", unsafe_allow_html=True)

    # Translation
    if lang == "Marathi":
        st.info("🌐 Translating summary to Marathi...")
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

    # 🔊 Audio section
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

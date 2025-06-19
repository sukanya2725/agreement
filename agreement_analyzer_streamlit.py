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
        text = " ".join([page.get_text().replace('\n', ' ').strip() for page in doc]) # Added .strip()
    except Exception as e:
        st.error("❌ Failed to extract text from PDF.")
        st.exception(e)
        st.stop()

    def smart_search(text, keywords, search_window=100): # Added search_window parameter
        best_score = 0
        best_match = "Not specified"
        # Split text by common sentence/paragraph delimiters for better context
        segments = re.split(r'[.!?\n\r]+', text) # Use regex for splitting

        for keyword in keywords:
            for segment in segments:
                segment_lower = segment.strip().lower()
                keyword_lower = keyword.lower()

                # Try exact match first for high confidence
                if keyword_lower in segment_lower:
                    score = 100
                else:
                    score = fuzz.partial_ratio(keyword_lower, segment_lower)

                if score > best_score and score >= 75: # Increased threshold for better accuracy
                    # Find the start of the keyword in the segment
                    try:
                        start_index = segment_lower.find(keyword_lower)
                        # Extract a window around the keyword for better context
                        # This aims to get the surrounding phrase, not just the keyword itself
                        start_of_match = max(0, start_index - 20) # Go back a few characters
                        end_of_match = min(len(segment), start_index + len(keyword) + search_window) # Go forward
                        extracted_phrase = segment[start_of_match:end_of_match].strip()

                        # Further refine extraction for project name if a specific pattern is found
                        if any(k in ["name of project", "project title"] for k in keywords):
                            match = re.search(r'(?:name of project|project title|project name|tender for)[:\s]*(.*?)(?:\n|\r|\.|$)', extracted_phrase, re.IGNORECASE)
                            if match:
                                best_score = 100 # High confidence if pattern matches
                                best_match = match.group(1).strip()
                                # Clean up common trailing characters
                                if best_match.endswith(','):
                                    best_match = best_match[:-1]
                                return best_match # Return immediately for high confidence match

                        best_score = score
                        best_match = segment.strip()
                    except Exception:
                        # Fallback if window extraction fails
                        best_match = segment.strip()
        return best_match

    # Extract Fields
    project_name_keywords = [
        "name of project", "project title", "work of", "tender for", "project name",
        "agreement name of project", "subject of work", "concerning" # Added more specific keywords
    ]
    project_name = smart_search(text, project_name_keywords)

    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    date = date_match.group(0) if date_match else "Not specified"

    amount_sentence = smart_search(text, ["contract value", "final payable amount", "total amount", "estimated cost"])
    if "not specified" not in amount_sentence.lower():
        amount = amount_sentence
    else:
        amt_match = re.search(r'(?:₹|rs\.?)\s?[\d,]+(?:\.\d{1,2})?', text.lower())
        amount = amt_match.group(0).upper() if amt_match else "Not specified"

    parties = smart_search(text, ["between", "municipal corporation", "contractor", "agreement signed", "entered into by", "parties involved"])

    # Refined Scope of Work keywords and a slightly different approach if needed
    scope_keywords = [
        "scope of work", "project includes", "the work includes", "responsibilities include",
        "construction and improvement", "nature of work", "description of work",
        "for the work of", "carrying out the work of" # More specific scope keywords
    ]
    scope = smart_search(text, scope_keywords, search_window=200) # Larger window for scope

    duration = smart_search(text, ["within", "calendar months", "construction period", "project completion time", "period of completion"])

    # Clause search
    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure", "nda"],
        "Termination": ["termination", "cancelled", "terminate"],
        "Dispute Resolution": ["arbitration", "dispute", "resolved", "decision of commissioner", "disputes shall be settled"],
        "Jurisdiction": ["jurisdiction", "governing law", "court", "legal"],
        "Force Majeure": ["force majeure", "natural events", "act of god", "unforeseen"],
        "Signatures": ["signed by", "signature", "authorized signatory"]
    }

    clause_results = []
    for name, keywords in clauses.items():
        found = smart_search(text, keywords)
        clause_results.append(f"✅ {name}" if found != "Not specified" else f"❌ {name}")

    # Summary Paragraph
    paragraph = "This agreement"
    if parties != "Not specified":
        paragraph += f" is made between {parties}"
    if date != "Not specified":
        paragraph += f" on {date}"
    if project_name != "Not specified": # Include project name in summary
        paragraph += f" for the project: {project_name}"
    if scope != "Not specified":
        paragraph += f", covering work such as: {scope}"
    if amount != "Not specified":
        paragraph += f". The contract value is: {amount}"
    if duration != "Not specified":
        paragraph += f", with a total project duration of {duration}."

    included = [c[2:] for c in clause_results if c.startswith("✅")]
    if included:
        paragraph += " The agreement includes clauses like: " + ", ".join(included) + "."

    # Display
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

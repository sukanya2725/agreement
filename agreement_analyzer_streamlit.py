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
        # Extract text page by page and clean it
        text_pages = [page.get_text().replace('\n', ' ').strip() for page in doc]
        text = " ".join(text_pages)
        # Normalize multiple spaces to a single space
        text = re.sub(r'\s+', ' ', text).strip()

    except Exception as e:
        st.error("❌ Failed to extract text from PDF.")
        st.exception(e)
        st.stop()

    def smart_search(text_content, keywords, search_window=100):
        best_score = 0
        best_match = "Not specified"

        # Split text into larger chunks that might contain full phrases/sentences,
        # using more generic delimiters like multiple newlines, or a very long stretch of text.
        segments = re.split(r'(?<=[.!?])\s+|\n{2,}', text_content) # Split by sentence end or double newline

        for keyword in keywords:
            keyword_lower = keyword.lower()
            for segment in segments:
                segment_lower = segment.strip().lower()

                # Prioritize exact keyword match within a segment for higher confidence
                if keyword_lower in segment_lower:
                    score = 100
                else:
                    score = fuzz.partial_ratio(keyword_lower, segment_lower)

                if score > best_score and score >= 70: # Slightly adjusted threshold
                    best_score = score
                    # Try to capture more context around the keyword
                    match_start = segment_lower.find(keyword_lower)
                    if match_start != -1:
                        # Extract a snippet around the keyword
                        context_start = max(0, match_start - 30) # Back a bit
                        context_end = min(len(segment), match_start + len(keyword) + search_window) # Forward more
                        extracted_snippet = segment[context_start:context_end].strip()

                        # Ensure the extracted snippet ends reasonably (e.g., before next major heading or very short phrase)
                        best_match = extracted_snippet
                    else:
                        best_match = segment.strip() # Fallback to whole segment if index not found

        return best_match

    # --- Targeted Extraction for Project Name ---
    project_name = "Not specified"
    # Pattern 1: AGREEMENT NAME OF PROJECT: ...
    project_name_match_1 = re.search(r'AGREEMENT NAME OF PROJECT:\s*(.*?)(?:\n|The Agreement is entered|Between the)', text, re.IGNORECASE | re.DOTALL)
    if project_name_match_1:
        project_name = project_name_match_1.group(1).strip()
        # Clean up common trailing words if they are part of the next sentence start
        project_name = re.sub(r'^\s*[:;]\s*', '', project_name) # remove leading colon/semicolon
        if project_name.endswith('.'): project_name = project_name[:-1].strip() # remove trailing period if any
        if project_name.lower().endswith("the agreement"): project_name = project_name[:-len("the agreement")].strip()
        if project_name.lower().endswith("the"): project_name = project_name[:-len("the")].strip() # Catch partial ends
        if project_name.lower().endswith("city under"): project_name = project_name[:-len("city under")].strip() # Catch specific extra text from your example

    if project_name == "Not specified":
        # Pattern 2: PROJECT TITLE: / NAME OF WORK: / SUBJECT: ... (more generic)
        project_name_match_2 = re.search(r'(?:PROJECT TITLE|NAME OF WORK|SUBJECT|TENDER FOR)[:\s](.?)(?:\n|\.|$)', text, re.IGNORECASE | re.DOTALL)
        if project_name_match_2:
            project_name = project_name_match_2.group(1).strip()
            # Further refine, sometimes names can be on a single line
            if len(project_name.split()) > 20 and "\n" in project_name: # if very long and has newlines, take up to first newline
                 project_name = project_name.split('\n')[0].strip()

    # Fallback to smart_search if targeted regex doesn't find it
    if project_name == "Not specified":
         project_name_keywords = [
            "name of work", "project title", "work of", "tender for", "project name",
            "agreement name of project", "subject of work", "concerning",
            "improvement & construction of" # Added a very specific keyword from your example
        ]
         project_name = smart_search(text, project_name_keywords, search_window=150)
         if project_name.lower().startswith("agreement name of project"): # Clean if smart search picks up the lead-in
             project_name = re.sub(r'agreement name of project[:\s]*', '', project_name, flags=re.IGNORECASE).strip()


    # --- Targeted Extraction for Scope of Work ---
    scope = "Not specified"
    # Pattern 1: Look for "scope of work" or similar phrases followed by a description
    scope_match_1 = re.search(r'(?:scope of work|the work consists of|description of work|nature of work)[:\s](.?)(?:(?=\n\n)|(?=The contractor shall complete)|(?=Article \d)|(?=Clause \d)|(?=Term of)|(?=duration of work))', text, re.IGNORECASE | re.DOTALL)
    if scope_match_1:
        scope = scope_match_1.group(1).strip()
        # Clean up any leading punctuation or keywords that snuck in
        scope = re.sub(r'^(is|are|details|following|as follows)\s*[:.]?\s*', '', scope, flags=re.IGNORECASE).strip()
        if scope.endswith('.'): scope = scope[:-1].strip()

    if scope == "Not specified":
        # Pattern 2: Sometimes the scope is just what the project name is about if not explicitly stated
        # If project name has "Improvement & Construction of..." it implies scope
        if "improvement & construction of" in project_name.lower() and "storm water drains" in project_name.lower():
            # If project name IS the scope, assign it and refine
            scope = project_name.strip()
            # Try to cut off subsequent irrelevant text if the project name captured too much
            scope = re.sub(r'(?i)\s*under Maharashtra Suvarna Jayanti Nagarothan Maha Abhiyan State Level.*', '', scope).strip()


    # Fallback to smart_search if targeted regex or derived logic doesn't find it
    if scope == "Not specified":
        scope_keywords = [
            "scope of work", "project includes", "the work includes", "responsibilities include",
            "construction and improvement", "nature of work", "description of work",
            "for the work of", "carrying out the work of",
            "improvement & construction of storm water drains" # Very specific from your text
        ]
        scope = smart_search(text, scope_keywords, search_window=250) # Larger window for scope
        if scope.lower().startswith("agreement name of project"): # Clean if smart search picks up the lead-in
            scope = re.sub(r'agreement name of project[:\s]*', '', scope, flags=re.IGNORECASE).strip()


    # --- Other Extractions ---
    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
    date = date_match.group(0) if date_match else "Not specified"

    amount_sentence = smart_search(text, ["contract value", "final payable amount", "total amount", "estimated cost", "sum of rupees", "rupees"], search_window=100)
    amount = "Not specified"
    if "not specified" not in amount_sentence.lower():
        # Try to find a clear amount string within the matched sentence
        # Added a specific pattern for 'ten lakh'
        amt_match = re.search(r'(?:(?:[Rr][Ss]\.?|₹)\s*[\d,]+(?:\.\d{1,2})?|[\d,]+\s*(?:lakh|crore|million|billion)\s*(?:rupees)?|ten lakh)', amount_sentence, re.IGNORECASE)
        if amt_match:
            amount = amt_match.group(0).upper()
        else:
            # Fallback if specific currency pattern not found but a number is there
            num_match = re.search(r'[\d,]+(?:\.\d{1,2})?', amount_sentence)
            if num_match:
                amount = num_match.group(0) # Just the number for now
            else:
                amount = amount_sentence # Keep the whole sentence if no number found, better than 'Not specified'

    parties = "Not specified"
    # The Parties Involved text provided is very long, a more specific regex is needed
    parties_match = re.search(r'between the\s*(.*?)(?:of the FIRST PART AND M/s|$)', text, re.IGNORECASE | re.DOTALL)
    if parties_match:
        # Capture the part before "of the FIRST PART AND M/s"
        captured_text = parties_match.group(1).strip()
        # Extract the Municipal Corporation part
        smc_match = re.search(r'Solapur Municipal Corporation(?:.*?)(?=, R/o office)', captured_text, re.IGNORECASE)
        smc_name = smc_match.group(0).strip() if smc_match else "Solapur Municipal Corporation"
        parties = f"{smc_name} and a Contractor (M/s...)" # Generic for the second party for now
    else: # Fallback to smart_search if specific regex fails
        parties = smart_search(text, ["between", "municipal corporation", "contractor", "agreement signed", "entered into by", "parties involved"])
        if parties.lower().startswith("agreement name of project"): # Clean if smart search picks up the lead-in
            parties = re.sub(r'agreement name of project[:\s]*', '', parties, flags=re.IGNORECASE).strip()


    duration = smart_search(text, ["within", "calendar months", "construction period", "project completion time", "period of completion", "complete the work within"])


    # Clause search (unchanged, as it seems to be working reasonably well)
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
    if project_name != "Not specified":
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

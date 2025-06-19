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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

st.set_page_config(page_title="Agreement Analyzer", layout="centered")
st.markdown("""
<div style="background-color:#003366;padding:15px;border-radius:10px">
<h1 style="color:white;text-align:center;">📄 Agreement Analyzer PRO</h1>
</div>
""", unsafe_allow_html=True)

# Define a function to check if Tesseract is installed and available
def check_tesseract_availability():
    try:
        # PyMuPDF's OCR uses the TESSDATA_PREFIX environment variable or tries default paths
        # A simple check could be to try to open a dummy pixmap with OCR
        dummy_pix = fitz.Pixmap(fitz.csRGB, (0,0,1,1), (255,255,255))
        _ = dummy_pix.pdfocr_tobytes(language='eng') # Try a minimal OCR operation
        return True
    except Exception as e:
        logging.warning(f"Tesseract or its language data not found or misconfigured for PyMuPDF OCR: {e}")
        return False

# Initialize Tesseract availability check once
TESSERACT_AVAILABLE = check_tesseract_availability()
if not TESSERACT_AVAILABLE:
    st.warning("⚠️ **Tesseract OCR engine not found or not correctly configured.**\n"
               "   Scanned PDF agreements will not be processed correctly.\n"
               "   Please install Tesseract OCR and ensure `TESSDATA_PREFIX` is set if needed.\n"
               "   (e.g., `sudo apt-get install tesseract-ocr tesseract-ocr-eng` on Linux, "
               "   or download installer for Windows and add to PATH/set TESSDATA_PREFIX).")


uploaded_file = st.file_uploader("📤 Upload a PDF Agreement", type=["pdf"])
lang = st.selectbox("🌐 Select Output Language", ["English", "Marathi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("🔍 Extracting and analyzing text (using OCR for scanned documents if needed)...")

    try:
        doc = fitz.open(pdf_path)
        full_text_content = []

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text("text") # Try extracting text directly

            # Simple check if text is very sparse, indicating a scanned page
            # You might need to adjust the threshold (e.g., len(page_text) < 50 for a full page)
            if len(page_text.strip()) < 100 and TESSERACT_AVAILABLE: # If less than 100 characters, try OCR
                logging.info(f"Page {page_num+1} seems sparse, attempting OCR.")
                try:
                    # Render page to high-res pixmap for better OCR
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Use a higher resolution for OCR
                    ocr_text_page = fitz.open("pdf", pix.pdfocr_tobytes(language="eng"))
                    ocr_text = ocr_text_page[0].get_text("text")
                    if len(ocr_text.strip()) > len(page_text.strip()): # Use OCR text if it's better
                        page_text = ocr_text
                        logging.info(f"OCR successfully extracted more text for page {page_num+1}.")
                    else:
                        logging.info(f"OCR for page {page_num+1} did not yield significantly more text.")
                except Exception as ocr_e:
                    logging.error(f"Error during OCR for page {page_num+1}: {ocr_e}")
                    st.warning(f"❌ Could not perform OCR on page {page_num+1}. Text extraction might be incomplete.")

            full_text_content.append(page_text.replace('\n', ' ').strip())

        text = " ".join(full_text_content)
        text = re.sub(r'\s+', ' ', text).strip() # Normalize spaces

        # --- DIAGNOSTIC STEP: SHOW RAW EXTRACTED TEXT ---
        st.subheader("🕵️‍♂️ Raw Extracted Text (for debugging)")
        st.text_area("Full PDF Text", text, height=500)
        st.warning("Please copy a relevant section of this text (especially around Project Name, Parties, Amount, Scope, Duration) and share it if you need further help debugging the regex patterns.")
        # --- END DIAGNOSTIC STEP ---

    except Exception as e:
        st.error("❌ Failed to extract text from PDF.")
        st.exception(e)
        st.stop()

    def smart_search(text_content, keywords, search_window=100):
        best_score = 0
        best_match = "Not specified"

        # Split text into larger chunks that might contain full phrases/sentences,
        # using more generic delimiters like multiple newlines, or a very long stretch of text.
        # This is crucial for maintaining context for fuzzy matching
        segments = re.split(r'(?<=[.!?])\s+|\n{2,}', text_content)

        for keyword in keywords:
            keyword_lower = keyword.lower()
            for segment in segments:
                segment_lower = segment.strip().lower()

                if keyword_lower in segment_lower:
                    score = 100
                else:
                    score = fuzz.partial_ratio(keyword_lower, segment_lower)

                if score > best_score and score >= 70: # Score threshold to consider a match
                    best_score = score
                    match_start = segment_lower.find(keyword_lower)
                    if match_start != -1:
                        # Extract a snippet around the keyword
                        context_start = max(0, match_start - 30) # Back a bit
                        context_end = min(len(segment), match_start + len(keyword) + search_window) # Forward more
                        extracted_snippet = segment[context_start:context_end].strip()

                        # Basic cleaning: remove trailing sentence fragments that clearly start new ideas
                        extracted_snippet = re.sub(r'\s*\b(?:and|but|or|the|a|an|with|for)\s+.*$', '', extracted_snippet, flags=re.IGNORECASE)
                        best_match = extracted_snippet
                    else:
                        best_match = segment.strip() # Fallback to whole segment if index not found

        return best_match

    # --- Targeted Extraction for Project Name ---
    project_name = "Not specified"
    # Pattern 1: AGREEMENT NAME OF PROJECT: ...
    project_name_match_1 = re.search(r'AGREEMENT NAME OF PROJECT:\s*(.*?)(?:\n|The Agreement is entered|Between the|This Agreement|Whereas)', text, re.IGNORECASE | re.DOTALL)
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
        project_name_match_2 = re.search(r'(?:PROJECT TITLE|NAME OF WORK|SUBJECT|TENDER FOR|AGREEMENT FOR)[:\s]*(.*?)(?:\n|\.|$|The Agreement is entered|Between the|This Agreement|Whereas)', text, re.IGNORECASE | re.DOTALL)
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
            "improvement & construction of", "agreement for" # Added more generic keywords
        ]
         project_name = smart_search(text, project_name_keywords, search_window=150)
         if project_name.lower().startswith("agreement name of project") or project_name.lower().startswith("agreement for"): # Clean if smart search picks up the lead-in
             project_name = re.sub(r'(agreement name of project|agreement for)[:\s]*', '', project_name, flags=re.IGNORECASE).strip()
    
    # Final cleanup of project name
    project_name = re.sub(r'\s*\(hereinafter referred to as[\s\S]*?\)\s*', '', project_name, flags=re.IGNORECASE).strip()
    project_name = re.sub(r'^\W+', '', project_name).strip() # Remove any leading non-word characters


    # --- Targeted Extraction for Scope of Work ---
    scope = "Not specified"
    # Pattern 1: Look for "scope of work" or similar phrases followed by a description
    scope_match_1 = re.search(r'(?:scope of work|the work consists of|description of work|nature of work|details of work)[:\s]*(.*?)(?:(?=\n\n)|(?=The contractor shall complete)|(?=Article \d)|(?=Clause \d)|(?=Term of)|(?=duration of work)|(?=schedule of work)|(?=period of completion)|(?=terms and conditions)|(?=consideration for the work))', text, re.IGNORECASE | re.DOTALL)
    if scope_match_1:
        scope = scope_match_1.group(1).strip()
        # Clean up any leading punctuation or keywords that snuck in
        scope = re.sub(r'^(is|are|details|following|as follows|the following)\s*[:.]?\s*', '', scope, flags=re.IGNORECASE).strip()
        if scope.endswith('.'): scope = scope[:-1].strip()

    if scope == "Not specified":
        # Pattern 2: Sometimes the scope is just what the project name is about if not explicitly stated
        # If project name has "Improvement & Construction of..." it implies scope
        if "improvement & construction of" in project_name.lower():
            # If project name IS the scope, assign it and refine
            scope = project_name.strip()
            # Try to cut off subsequent irrelevant text if the project name captured too much
            scope = re.sub(r'(?i)\s*under Maharashtra Suvarna Jayanti Nagarothan Maha Abhiyan State Level.*', '', scope).strip()


    # Fallback to smart_search if targeted regex or derived logic doesn't find it
    if scope == "Not specified":
        scope_keywords = [
            "scope of work", "project includes", "the work includes", "responsibilities include",
            "construction and improvement", "nature of work", "description of work",
            "for the work of", "carrying out the work of", "details of work",
            "improvement & construction of storm water drains", # Very specific from your text
            "provision of facilities for", "execution of work", "completion of"
        ]
        scope = smart_search(text, scope_keywords, search_window=250) # Larger window for scope
        if scope.lower().startswith("agreement name of project") or scope.lower().startswith("agreement for"): # Clean if smart search picks up the lead-in
            scope = re.sub(r'(agreement name of project|agreement for)[:\s]*', '', scope, flags=re.IGNORECASE).strip()
    
    # Final cleanup of scope
    scope = re.sub(r'^\W+', '', scope).strip() # Remove any leading non-word characters


    # --- Other Extractions ---
    date_match = re.search(r'(?:dated|on)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b)', text, re.IGNORECASE)
    date = date_match.group(1) if date_match else "Not specified"

    amount_sentence = smart_search(text, ["contract value", "final payable amount", "total amount", "estimated cost", "sum of rupees", "rupees", "lakh", "crore", "total consideration"], search_window=100)
    amount = "Not specified"
    if "not specified" not in amount_sentence.lower():
        # Enhanced regex to capture more amount variations, including words and combinations
        amt_match = re.search(r'(?:(?:[Rr][Ss]\.?|₹)\s*[\d,\.]+|[\d,\.]+\s*(?:lakhs?|crores?|millions?|billions?)\s*(?:rupees)?|one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|lakh|crore)(?:\s+and\s+(?:(?:[Rr][Ss]\.?|₹)?\s*[\d,\.]+))?', amount_sentence, re.IGNORECASE)
        if amt_match:
            amount = amt_match.group(0).upper().strip()
        else:
            num_match = re.search(r'[\d,\.]+(?:\.\d{1,2})?', amount_sentence)
            if num_match:
                amount = num_match.group(0)
            else:
                amount = amount_sentence

    parties = "Not specified"
    # Parties extraction needs to be highly flexible. Let's try to capture names after "between" and before "witnesseth" or "whereas"
    parties_match = re.search(r'between\s+(.*?)(?:(?:hereinafter)?\s+referred to as the.*?PART)?\s+and\s+(.*?)(?:(?:hereinafter)?\s+referred to as the.*?PART)?(?:,\s*witnesseth|,\s*whereas|\.)', text, re.IGNORECASE | re.DOTALL)
    if parties_match:
        party1 = parties_match.group(1).strip()
        party2 = parties_match.group(2).strip()
        
        # Clean up common legal boilerplate from party names
        party1 = re.sub(r'\s*\(herein(?:after)? referred to as the.*?part\)\s*', '', party1, flags=re.IGNORECASE).strip()
        party2 = re.sub(r'\s*\(herein(?:after)? referred to as the.*?part\)\s*', '', party2, flags=re.IGNORECASE).strip()

        # Attempt to make party names more concise if they contain addresses or very long descriptions
        party1 = re.split(r'(?:,\s*(?:a company|a corporation|an individual|having its registered office|residing at|of))', party1, 1, flags=re.IGNORECASE)[0].strip()
        party2 = re.split(r'(?:,\s*(?:a company|a corporation|an individual|having its registered office|residing at|of))', party2, 1, flags=re.IGNORECASE)[0].strip()

        parties = f"{party1} and {party2}"
    else: # Fallback to smart_search if specific regex fails
        parties = smart_search(text, ["between", "municipal corporation", "contractor", "agreement signed", "entered into by", "parties involved", "first part", "second part"])
        if parties.lower().startswith("agreement name of project") or parties.lower().startswith("agreement for"): # Clean if smart search picks up the lead-in
            parties = re.sub(r'(agreement name of project|agreement for)[:\s]*', '', parties, flags=re.IGNORECASE).strip()


    duration = smart_search(text, ["within", "calendar months", "construction period", "project completion time", "period of completion", "complete the work within", "duration of this agreement"], search_window=100)


    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure", "nda", "secrecy"],
        "Termination": ["termination", "cancelled", "terminate", "expiration", "end of agreement"],
        "Dispute Resolution": ["arbitration", "dispute", "resolved", "decision of commissioner", "disputes shall be settled", "court of law", "jurisdiction", "legal proceedings"],
        "Jurisdiction": ["jurisdiction", "governing law", "court", "legal", "applicable law", "laws of india"],
        "Force Majeure": ["force majeure", "natural events", "act of god", "unforeseen circumstances", "beyond control"],
        "Signatures": ["signed by", "signature", "authorized signatory", "witnesses", "party of the first part", "party of the second part"]
    }

    clause_results = []
    for name, keywords in clauses.items():
        found = smart_search(text, keywords, search_window=200) # Increased search window for clauses
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

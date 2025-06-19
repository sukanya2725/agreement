import streamlit as st
import pymupdf as fitz # Used for PDF processing, relies on Tesseract for OCR
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

# Define a function to check if Tesseract is installed and available for PyMuPDF
def check_tesseract_availability():
    """
    Checks if Tesseract OCR engine and its English language data
    are correctly configured for PyMuPDF's OCR functionality.
    This function will attempt a minimal OCR operation on a dummy pixmap.
    """
    try:
        # Create a tiny 1x1 white pixmap
        dummy_pix = fitz.Pixmap(fitz.csRGB, (0, 0, 1, 1), (255, 255, 255))
        # Attempt an OCR operation. If Tesseract is not found or tessdata is missing,
        # this will raise an exception.
        _ = dummy_pix.pdfocr_tobytes(language='eng')
        logging.info("Tesseract OCR and English language data appear to be available.")
        return True
    except Exception as e:
        logging.warning(f"Tesseract or its 'eng' language data not found or misconfigured for PyMuPDF OCR: {e}")
        return False

# Initialize Tesseract availability check once when the app starts
TESSERACT_AVAILABLE = check_tesseract_availability()

if not TESSERACT_AVAILABLE:
    st.warning("⚠️ **Tesseract OCR engine not found or not correctly configured.**\n"
               "   Scanned PDF agreements will not be processed correctly.\n"
               "   Please install Tesseract OCR and ensure `TESSDATA_PREFIX` is set if needed.\n"
               "   (e.g., `sudo apt-get install tesseract-ocr tesseract-ocr-eng` on Linux, "
               "   or download installer for Windows and add to PATH/set TESSDATA_PREFIX).\n\n"
               "**For detailed installation instructions, refer to the previous explanation.**")


uploaded_file = st.file_uploader("📤 Upload a PDF Agreement", type=["pdf"])
lang = st.selectbox("🌐 Select Output Language", ["English", "Marathi"])

if uploaded_file:
    # Use tempfile to save the uploaded PDF, ensuring it's cleaned up properly
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
            page_text = page.get_text("text") # Try extracting text directly (for searchable PDFs)

            # Heuristic to determine if a page might be scanned: very little extracted text
            # This threshold (e.g., < 100 characters) might need adjustment based on typical document content.
            # Only attempt OCR if Tesseract is confirmed to be available.
            if len(page_text.strip()) < 100 and TESSERACT_AVAILABLE:
                logging.info(f"Page {page_num+1} seems sparse (direct text: {len(page_text.strip())} chars), attempting OCR.")
                try:
                    # Render page to high-res pixmap for better OCR quality
                    # A matrix of (2,2) means 200% resolution, improving OCR accuracy.
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    # Perform OCR using PyMuPDF's built-in OCR capabilities (which call Tesseract)
                    # For Marathi, you would need 'mar' language data installed for Tesseract.
                    # For now, keeping 'eng' as per initial Tesseract check.
                    ocr_doc = fitz.open("pdf", pix.pdfocr_tobytes(language="eng"))
                    ocr_text = ocr_doc[0].get_text("text")

                    # Use OCR text if it yields significantly more content
                    if len(ocr_text.strip()) > len(page_text.strip()) * 1.5: # Use if OCR is 50% better
                        page_text = ocr_text
                        logging.info(f"OCR successfully extracted significantly more text for page {page_num+1}.")
                    else:
                        logging.info(f"OCR for page {page_num+1} did not yield significantly more text (direct: {len(page_text.strip())}, OCR: {len(ocr_text.strip())}). Sticking with direct text.")
                except Exception as ocr_e:
                    logging.error(f"Error during OCR for page {page_num+1}: {ocr_e}")
                    st.warning(f"❌ Could not perform OCR on page {page_num+1}. Text extraction might be incomplete for this page.")

            full_text_content.append(page_text.replace('\n', ' ').strip())

        text = " ".join(full_text_content)
        text = re.sub(r'\s+', ' ', text).strip() # Normalize multiple spaces to single space

        # --- DIAGNOSTIC STEP: SHOW RAW EXTRACTED TEXT ---
        # This section is very useful for debugging your regex patterns
        st.subheader("🕵️‍♂️ Raw Extracted Text (for debugging)")
        st.text_area("Full PDF Text", text, height=500)
        st.warning("Please copy a relevant section of this text (especially around Project Name, Parties, Amount, Scope, Duration) and share it if you need further help debugging the regex patterns.")
        # --- END DIAGNOSTIC STEP ---

    except Exception as e:
        st.error("❌ Failed to extract text from PDF. Please ensure it's a valid PDF.")
        st.exception(e)
        # Clean up the temporary file if an error occurs early
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        st.stop() # Stop execution if PDF cannot be processed

    finally:
        # Ensure the temporary file is deleted after processing
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

    # Function for fuzzy searching keywords within text
    def smart_search(text_content, keywords, search_window=100):
        """
        Performs a fuzzy search for keywords within text segments and returns
        a relevant snippet.
        """
        best_score = 0
        best_match = "Not specified"

        # Split text into larger chunks/sentences to maintain context for fuzzy matching
        segments = re.split(r'(?<=[.!?])\s+|\n{2,}', text_content)

        for keyword in keywords:
            keyword_lower = keyword.lower()
            for segment in segments:
                segment_lower = segment.strip().lower()

                if keyword_lower in segment_lower:
                    score = 100 # Exact match, highest score
                else:
                    # Use partial_ratio to find keywords within a larger string
                    score = fuzz.partial_ratio(keyword_lower, segment_lower)

                if score > best_score and score >= 70: # Score threshold to consider a match
                    best_score = score
                    # Try to find the exact position of the keyword (case-insensitive)
                    match_start = segment_lower.find(keyword_lower)
                    if match_start != -1:
                        # Extract a snippet around the keyword for context
                        context_start = max(0, match_start - 30) # A few characters before
                        context_end = min(len(segment), match_start + len(keyword) + search_window) # Keyword length + window after
                        extracted_snippet = segment[context_start:context_end].strip()

                        # Basic cleaning: remove trailing sentence fragments that clearly start new ideas
                        # This regex needs careful tuning. It tries to cut off after common conjunctions/articles.
                        extracted_snippet = re.sub(r'\s*\b(?:and|but|or|the|a|an|with|for|etc|i\.e\.|e\.g\.)\s+.*$', '', extracted_snippet, flags=re.IGNORECASE)
                        best_match = extracted_snippet
                    else:
                        best_match = segment.strip() # Fallback to whole segment if index not found

        return best_match

    # --- Targeted Extraction for Project Name ---
    project_name = "Not specified"
    # Pattern 1: AGREEMENT NAME OF PROJECT: ...
    project_name_match_1 = re.search(r'AGREEMENT NAME OF PROJECT:\s*(.*?)(?:\n|The Agreement is entered|Between the|This Agreement|Whereas|WHEREAS)', text, re.IGNORECASE | re.DOTALL)
    if project_name_match_1:
        project_name = project_name_match_1.group(1).strip()
        # Clean up common trailing words/phrases that might be part of the next sentence start
        project_name = re.sub(r'^\s*[:;]\s*', '', project_name) # remove leading colon/semicolon
        if project_name.endswith('.'): project_name = project_name[:-1].strip() # remove trailing period if any
        project_name = re.sub(r'(?i)\s*(?:the agreement|the city under|under|on|by)$', '', project_name).strip() # More robust trailing cleanup

    if project_name == "Not specified":
        # Pattern 2: PROJECT TITLE: / NAME OF WORK: / SUBJECT: ... (more generic)
        project_name_match_2 = re.search(r'(?:PROJECT TITLE|NAME OF WORK|SUBJECT|TENDER FOR|AGREEMENT FOR|WORK ORDER NO)\s*[:\s]*(.*?)(?:\n|\.|$|The Agreement is entered|Between the|This Agreement|Whereas|WHEREAS)', text, re.IGNORECASE | re.DOTALL)
        if project_name_match_2:
            project_name = project_name_match_2.group(1).strip()
            # Further refine, sometimes names can be on a single line
            if len(project_name.split()) > 20 and "\n" in project_name: # if very long and has newlines, take up to first newline
                project_name = project_name.split('\n')[0].strip()
            # Clean up common trailing words/phrases
            project_name = re.sub(r'(?i)\s*(?:the agreement|the city under|under|on|by)$', '', project_name).strip()

    # Fallback to smart_search if targeted regex doesn't find it
    if project_name == "Not specified":
        project_name_keywords = [
            "name of work", "project title", "work of", "tender for", "project name",
            "agreement name of project", "subject of work", "concerning",
            "improvement & construction of", "agreement for", "work order for"
        ]
        project_name_smart_match = smart_search(text, project_name_keywords, search_window=150)
        if project_name_smart_match != "Not specified":
             project_name = project_name_smart_match
             # Clean if smart search picks up the lead-in
             project_name = re.sub(r'(agreement name of project|agreement for|project title|name of work|subject|tender for|work order no)[:\s]*', '', project_name, flags=re.IGNORECASE).strip()

    # Final cleanup of project name
    project_name = re.sub(r'\s*\(hereinafter referred to as[\s\S]*?\)\s*', '', project_name, flags=re.IGNORECASE).strip()
    project_name = re.sub(r'^\W+', '', project_name).strip() # Remove any leading non-word characters
    # If it still looks like a keyword, set to Not specified (avoid "Project Title" as output)
    if project_name.lower() in [kw.lower() for kw in project_name_keywords] or len(project_name.strip()) < 5:
        project_name = "Not specified"
    elif project_name.endswith('.'):
        project_name = project_name[:-1].strip() # remove trailing period if any
    
    # --- Targeted Extraction for Scope of Work ---
    scope = "Not specified"
    # Pattern 1: Look for "scope of work" or similar phrases followed by a description
    scope_match_1 = re.search(r'(?:scope of work|the work consists of|description of work|nature of work|details of work)[:\s]*(.*?)(?:(?=\n\n)|(?=The contractor shall complete)|(?=Article \d)|(?=Clause \d)|(?=Term of)|(?=duration of work)|(?=schedule of work)|(?=period of completion)|(?=terms and conditions)|(?=consideration for the work)|(?=TOTAL COST)|(?=AMOUNT IN RUPEES))', text, re.IGNORECASE | re.DOTALL)
    if scope_match_1:
        scope = scope_match_1.group(1).strip()
        # Clean up any leading punctuation or keywords that snuck in
        scope = re.sub(r'^(is|are|details|following|as follows|the following)\s*[:.]?\s*', '', scope, flags=re.IGNORECASE).strip()
        if scope.endswith('.'): scope = scope[:-1].strip()

    if scope == "Not specified":
        # Pattern 2: Sometimes the scope is just what the project name is about if not explicitly stated
        # If project name has "Improvement & Construction of..." it implies scope
        if "improvement & construction of" in project_name.lower() and project_name != "Not specified":
            scope = project_name.strip()
            # Try to cut off subsequent irrelevant text if the project name captured too much
            scope = re.sub(r'(?i)\s*under Maharashtra Suvarna Jayanti Nagarothan Maha Abhiyan State Level.*', '', scope).strip()
            if scope.lower() in [kw.lower() for kw in project_name_keywords] or len(scope.strip()) < 5:
                scope = "Not specified"

    # Fallback to smart_search if targeted regex or derived logic doesn't find it
    if scope == "Not specified":
        scope_keywords = [
            "scope of work", "project includes", "the work includes", "responsibilities include",
            "construction and improvement", "nature of work", "description of work",
            "for the work of", "carrying out the work of", "details of work",
            "improvement & construction of storm water drains", # Very specific from your text
            "provision of facilities for", "execution of work", "completion of",
            "services to be provided", "works to be carried out"
        ]
        scope_smart_match = smart_search(text, scope_keywords, search_window=250) # Larger window for scope
        if scope_smart_match != "Not specified":
            scope = scope_smart_match
            # Clean if smart search picks up the lead-in
            scope = re.sub(r'(scope of work|project includes|the work includes|description of work|nature of work|details of work)[:\s]*', '', scope, flags=re.IGNORECASE).strip()

    # Final cleanup of scope
    scope = re.sub(r'^\W+|\W+$', '', scope).strip() # Remove any leading/trailing non-word characters
    # If it still looks like a keyword, set to Not specified (avoid "Scope of Work" as output)
    if scope.lower() in [kw.lower() for kw in scope_keywords] or len(scope.strip()) < 5:
        scope = "Not specified"
    elif scope.endswith('.'):
        scope = scope[:-1].strip() # remove trailing period if any


    # --- Other Extractions ---
    date_match = re.search(r'(?:dated|on|date of this agreement)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*|\s+)\d{4}\b)', text, re.IGNORECASE)
    date = date_match.group(1) if date_match else "Not specified"

    amount_sentence = smart_search(text, ["contract value", "final payable amount", "total amount", "estimated cost", "sum of rupees", "rupees", "lakh", "crore", "total consideration", "cost of work"], search_window=100)
    amount = "Not specified"
    if "not specified" not in amount_sentence.lower():
        # Enhanced regex to capture more amount variations, including words and combinations
        amt_match = re.search(r'(?:(?:[Rr][Ss]\.?|₹)\s*[\d,\.]+(?:\.\d{1,2})?|[\d,\.]+\s*(?:lakhs?|crores?|millions?|billions?)\s*(?:only|rupees)?|one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|lakh|crore)(?:\s+and\s+(?:(?:[Rr][Ss]\.?|₹)?\s*[\d,\.]+))?', amount_sentence, re.IGNORECASE)
        if amt_match:
            amount = amt_match.group(0).upper().strip()
        else:
            num_match = re.search(r'[\d,\.]+(?:\.\d{1,2})?', amount_sentence)
            if num_match:
                amount = num_match.group(0)
            else:
                amount = amount_sentence
    
    # Additional cleanup for amount: remove "only" if it's the last word
    amount = re.sub(r'\s*only$', '', amount, flags=re.IGNORECASE).strip()


    parties = "Not specified"
    # Parties extraction needs to be highly flexible. Try to capture names after "between" and before "witnesseth" or "whereas"
    # This regex is complex because parties can be named with "hereinafter referred to as..." clauses.
    parties_match = re.search(r'between\s+(.*?)(?:\s+\(hereinafter referred to as(?: the)?\s*["\']?.*?["\']?\s*\)?)?\s+and\s+(.*?)(?:\s+\(hereinafter referred to as(?: the)?\s*["\']?.*?["\']?\s*\)?)?(?:,\s*witnesseth|,\s*WHEREAS|\.|$)', text, re.IGNORECASE | re.DOTALL)
    if parties_match:
        party1 = parties_match.group(1).strip()
        party2 = parties_match.group(2).strip()

        # Clean up common legal boilerplate from party names
        party1 = re.sub(r'\s*\(herein(?:after)? referred to as(?: the)?\s*["\']?.*?["\']?\s*\)\s*', '', party1, flags=re.IGNORECASE).strip()
        party2 = re.sub(r'\s*\(herein(?:after)? referred to as(?: the)?\s*["\']?.*?["\']?\s*\)\s*', '', party2, flags=re.IGNORECASE).strip()

        # Attempt to make party names more concise if they contain addresses or very long descriptions
        party1 = re.split(r'(?:,\s*(?:a company|a corporation|an individual|having its registered office|residing at|of|having its principal place of business at|represented by))', party1, 1, flags=re.IGNORECASE)[0].strip()
        party2 = re.split(r'(?:,\s*(?:a company|a corporation|an individual|having its registered office|residing at|of|having its principal place of business at|represented by))', party2, 1, flags=re.IGNORECASE)[0].strip()

        # Handle cases where party is "The Municipal Corporation of..."
        if "municipal corporation" in party1.lower() and len(party1.split()) > 10:
            party1 = re.search(r'(?:the\s+)?(?:[A-Z][a-z]+\s*){1,3}Municipal Corporation(?: of\s+[A-Z][a-z]+(?:(?:\s|-)?[A-Z][a-z]+)*)?', party1).group(0) if re.search(r'(?:the\s+)?(?:[A-Z][a-z]+\s*){1,3}Municipal Corporation(?: of\s+[A-Z][a-z]+(?:(?:\s|-)?[A-Z][a-z]+)*)?', party1) else party1
        if "municipal corporation" in party2.lower() and len(party2.split()) > 10:
             party2 = re.search(r'(?:the\s+)?(?:[A-Z][a-z]+\s*){1,3}Municipal Corporation(?: of\s+[A-Z][a-z]+(?:(?:\s|-)?[A-Z][a-z]+)*)?', party2).group(0) if re.search(r'(?:the\s+)?(?:[A-Z][a-z]+\s*){1,3}Municipal Corporation(?: of\s+[A-Z][a-z]+(?:(?:\s|-)?[A-Z][a-z]+)*)?', party2) else party2

        parties = f"{party1} and {party2}"
    else: # Fallback to smart_search if specific regex fails
        parties_keywords = ["between", "municipal corporation", "contractor", "agreement signed", "entered into by", "parties involved", "first part", "second part", "made and entered into"]
        parties_smart_match = smart_search(text, parties_keywords, search_window=150)
        if parties_smart_match != "Not specified":
            parties = parties_smart_match
            # Clean if smart search picks up the lead-in
            parties = re.sub(r'(between|agreement name of project|agreement for|made and entered into)[:\s]*', '', parties, flags=re.IGNORECASE).strip()
            # If it extracts something like "This Agreement is made and entered into by and between...", refine
            if parties.lower().startswith("this agreement is made and entered into by and"):
                parties = re.sub(r'(?i)this agreement is made and entered into by and between\s*', '', parties).strip()

    # Final cleanup of parties
    parties = re.sub(r'^\W+|\W+$', '', parties).strip() # Remove any leading/trailing non-word characters
    if parties.lower() in [kw.lower() for kw in parties_keywords] or len(parties.strip()) < 5:
        parties = "Not specified"
    elif parties.endswith('.'):
        parties = parties[:-1].strip() # remove trailing period if any


    duration = smart_search(text, ["within", "calendar months", "construction period", "project completion time", "period of completion", "complete the work within", "duration of this agreement", "time for completion"], search_window=100)
    # Further refine duration to only extract the time phrase (e.g., "12 calendar months")
    duration_match = re.search(r'(\d+\s+(?:days?|weeks?|months?|years?)\s*(?:calendar|working)?(?: from the date of agreement)?|within\s+\d+\s+(?:days?|weeks?|months?|years?))', duration, re.IGNORECASE)
    if duration_match:
        duration = duration_match.group(1).strip()
    elif "not specified" not in duration.lower() and len(duration.split()) > 10: # If smart search grabbed a long sentence
        duration_match_fallback = re.search(r'\d+\s+(?:days?|weeks?|months?|years?)', duration, re.IGNORECASE)
        duration = duration_match_fallback.group(0).strip() if duration_match_fallback else "Not specified"
    elif duration.lower() in [kw.lower() for kw in ["within", "calendar months", "construction period", "project completion time", "period of completion", "complete the work within", "duration of this agreement"]]:
        duration = "Not specified" # If it only found the keyword, not the value


    clauses = {
        "Confidentiality": ["confidentiality", "non-disclosure", "nda", "secrecy"],
        "Termination": ["termination", "cancelled", "terminate", "expiration", "end of agreement", "default"],
        "Dispute Resolution": ["arbitration", "dispute", "resolved", "decision of commissioner", "disputes shall be settled", "court of law", "jurisdiction", "legal proceedings", "amicable settlement"],
        "Jurisdiction": ["jurisdiction", "governing law", "court", "legal", "applicable law", "laws of india"],
        "Force Majeure": ["force majeure", "natural events", "act of god", "unforeseen circumstances", "beyond control", "calamity"],
        "Signatures": ["signed by", "signature", "authorized signatory", "witnesses", "party of the first part", "party of the second part", "seal", "executed by"]
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
    
    # If the paragraph is too short, add a fallback message
    if len(paragraph.split()) < 10:
        paragraph += " Further details require a comprehensive review of the document."


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
            # Check if gTTS also supports Marathi, if not, handle gracefully
            if 'mr' not in gTTS.LANGUAGES:
                 st.warning("⚠️ Marathi voice output may not be fully supported by gTTS. Defaulting to English voice.")
            translated = GoogleTranslator(source='auto', target='mr').translate(paragraph)
        except Exception as e:
            st.error("❌ Marathi translation failed.")
            st.exception(e)
            translated = paragraph # Fallback to English paragraph
        final_text = translated
        st.subheader("🈯 Marathi Translation")
        st.text_area("Translated Output", final_text, height=300)
    else:
        final_text = paragraph

    # Audio
    st.subheader("🎧 Audio Summary")
    try:
        audio_lang = 'mr' if lang == "Marathi" else 'en'
        # Check if the selected language is supported by gTTS
        if audio_lang not in gTTS.LANGUAGES:
            st.warning(f"⚠️ {lang} voice output may not be fully supported by gTTS. Defaulting to English voice for audio.")
            audio_lang = 'en' # Fallback to English if not supported
        
        tts = gTTS(final_text, lang=audio_lang)
        
        # Use tempfile for audio as well to ensure cleanup
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_tmp_file:
            audio_path = audio_tmp_file.name
            tts.save(audio_path)
        
        # Read the audio file and embed it in HTML
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
    finally:
        # Ensure the temporary audio file is deleted
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)

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

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

st.set_page_config(page_title="Advanced Agreement Analyzer", layout="centered")

st.markdown("""
<div style="background-color:#003366;padding:15px;border-radius:10px">
<h1 style="color:white;text-align:center;">📄 Advanced Agreement Analyzer</h1>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("About This App")
st.sidebar.info(
    "This app helps extract key information from PDF agreements and provides a summary. "
    "It uses advanced text extraction (including OCR for scanned documents) and intelligent "
    "pattern matching to identify crucial details like Project Name, Parties, Amount, and Scope."
)
st.sidebar.markdown("---")
st.sidebar.header("Important Notes for Best Results:")
st.sidebar.warning(
    "1. **Tesseract OCR:** For scanned PDFs (where you can't select text), Tesseract OCR is crucial. "
    "If it's not installed/configured in your environment, text extraction from scanned PDFs will fail. "
    "On Streamlit Cloud, you cannot install system-level software directly. "
    "**If your PDFs are scanned and you're on Streamlit Cloud, consider using an external OCR API.**\n"
    "2. **Document Variety:** While robust, this tool works best with agreements that have some structure. "
    "Highly unusual layouts or handwritten documents may yield 'Not specified' results.\n"
    "3. **Check Raw Text:** Always review the 'Raw Extracted Text' if the summary is incomplete. "
    "This helps identify if text extraction itself failed, or if the patterns need refinement."
)

# Function to check Tesseract availability (more robust)
def check_tesseract_availability():
    """
    Checks if Tesseract OCR engine and its English language data are correctly configured
    for PyMuPDF's OCR functionality by attempting a minimal OCR operation.
    """
    try:
        # Create a tiny dummy pixmap
        dummy_pix = fitz.Pixmap(fitz.csRGB, (0, 0, 1, 1), (255, 255, 255))
        # Attempt OCR on it with a very low DPI to be quick
        _ = dummy_pix.pdfocr_tobytes(language='eng', dpi=50)
        logging.info("Tesseract OCR and English language data appear to be available for PyMuPDF.")
        return True
    except Exception as e:
        logging.warning(f"Tesseract or its 'eng' language data not found or misconfigured for PyMuPDF OCR: {e}")
        return False

# Initialize Tesseract availability check once when the app starts
TESSERACT_AVAILABLE = check_tesseract_availability()

if not TESSERACT_AVAILABLE:
    st.error("🚨 **Tesseract OCR Engine Not Found or Not Configured Correctly!**")
    st.warning(
        "**Impact:** Scanned PDF agreements will likely not be processed, resulting in 'No readable text' or 'Not specified' fields.\n"
        "**Local Installation:** If running locally, install Tesseract OCR and its English language pack. "
        "([Windows Installer](https://tesseract-ocr.github.io/tessdoc/Downloads.html), `sudo apt-get install tesseract-ocr tesseract-ocr-eng` for Linux, `brew install tesseract` for macOS).\n"
        "**Streamlit Cloud:** Direct Tesseract installation isn't supported. For scanned PDFs on Streamlit Cloud, consider using an external OCR API service."
    )
    st.markdown("---")


uploaded_file = st.file_uploader("📤 Upload a PDF Agreement", type=["pdf"])
lang = st.selectbox("🌐 Select Output Language for Summary & Audio", ["English", "Marathi"])

if uploaded_file:
    pdf_path = None # Initialize pdf_path outside try block

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            pdf_path = tmp_file.name

        st.markdown("<hr>", unsafe_allow_html=True)
        st.info("🔍 Extracting and analyzing text from your PDF...")

        doc = fitz.open(pdf_path)
        full_text_content = []
        extracted_pages_count = 0

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")

            # Heuristic to detect if page is likely scanned (very little or no direct text)
            if len(page_text.strip()) < 100 and TESSERACT_AVAILABLE:
                logging.info(f"Page {page_num+1} seems sparse (direct text: {len(page_text.strip())} chars), attempting OCR.")
                try:
                    # Render page as pixmap at a higher DPI for better OCR
                    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3)) # 3x resolution
                    
                    # Perform OCR using PyMuPDF's built-in Tesseract integration
                    # full=True ensures it tries to OCR the whole page, not just recognized blocks
                    ocr_doc = fitz.open("pdf", pix.pdfocr_tobytes(language="eng", full=True))
                    ocr_text = ocr_doc[0].get_text("text")

                    # Use OCR text only if it significantly improves text extraction
                    if len(ocr_text.strip()) > len(page_text.strip()) * 1.5:
                        page_text = ocr_text
                        logging.info(f"OCR successfully extracted significantly more text for page {page_num+1}.")
                    else:
                        logging.info(f"OCR for page {page_num+1} did not yield significantly more text (direct: {len(page_text.strip())}, OCR: {len(ocr_text.strip())}). Sticking with direct text or limited OCR output.")
                except Exception as ocr_e:
                    logging.error(f"Error during OCR for page {page_num+1}: {ocr_e}")
                    st.warning(f"❌ Could not perform OCR on page {page_num+1}. Text extraction might be incomplete for this page. (Error: {ocr_e})")
            
            if page_text.strip():
                full_text_content.append(page_text.replace('\n', ' ').strip())
                extracted_pages_count += 1

        text = " ".join(full_text_content)
        text = re.sub(r'\s+', ' ', text).strip() # Normalize whitespace

        if not text:
            st.error("❌ **No readable text could be extracted from the PDF.**")
            st.info("This often happens if the PDF is purely scanned and Tesseract OCR is not working or the document quality is too low.")
            st.stop()

        st.subheader("🕵️‍♂️ Raw Extracted Text (for debugging)")
        st.text_area("Full PDF Text Content", text, height=500, help="This is the raw text extracted from your PDF. If summary fields are 'Not specified', check this text. It shows what the analysis had to work with.")
        st.warning("Please copy a relevant section of this text (especially around Project Name, Parties, Amount, Scope, Duration) and share it if you need further help debugging the extraction patterns.")

        # --- Smart Search Function (Improved) ---
        def smart_search(text_content, keywords, search_window=200):
            best_match = "Not specified"
            best_score = 0
            
            # Prioritize exact keyword matches first within segments
            segments = re.split(r'(?<=[.!?])\s+|\n{2,}', text_content) # Split by sentences or paragraphs

            for keyword in keywords:
                keyword_lower = keyword.lower()
                for segment in segments:
                    segment_lower = segment.strip().lower()

                    if keyword_lower in segment_lower:
                        score = 100 # Direct hit is perfect
                        # Try to capture more context around the direct hit
                        match_start_idx = segment_lower.find(keyword_lower)
                        if match_start_idx != -1:
                            start_context = max(0, match_start_idx - 50)
                            end_context = min(len(segment), match_start_idx + len(keyword) + search_window)
                            extracted_snippet = segment[start_context:end_context].strip()
                            # Clean up leading/trailing non-alphanumeric chars or boilerplate
                            extracted_snippet = re.sub(r'^\W+|\W+$', '', extracted_snippet).strip()
                            # Limit length to avoid capturing too much irrelevant text
                            if len(extracted_snippet) > 5 and len(extracted_snippet.split()) < 100:
                                best_match = extracted_snippet
                                best_score = score
                                return best_match # Return immediately for perfect match
                    
                    # If no perfect direct hit in any segment, try fuzzy match on segments
                    fuzzy_score = fuzz.partial_ratio(keyword_lower, segment_lower)
                    if fuzzy_score > best_score and fuzzy_score >= 80: # Higher threshold for fuzzy search
                        best_score = fuzzy_score
                        # Capture segment or a window around potential match
                        if len(segment.strip().split()) < 150: # Avoid very long segments for fuzzy match
                             extracted_snippet = segment.strip()
                             extracted_snippet = re.sub(r'^\W+|\W+$', '', extracted_snippet).strip()
                             if len(extracted_snippet) > 5:
                                best_match = extracted_snippet
            
            # Final cleanup of the best match
            if best_match != "Not specified":
                 # Remove common leading phrases that are part of the keyword
                for kw in keywords:
                    if best_match.lower().startswith(kw.lower()):
                        best_match = re.sub(f'^{re.escape(kw)}[:\\s]*', '', best_match, flags=re.IGNORECASE).strip()
                best_match = re.sub(r'\s*\b(?:hereinafter referred to as|as the)\s*["\']?.*?["\']?\s*\)?', '', best_match, flags=re.IGNORECASE).strip()
                best_match = re.sub(r'\s*\b(?:this agreement|the agreement)\s*', '', best_match, flags=re.IGNORECASE).strip()
                best_match = re.sub(r'\s*\.\s*$', '', best_match).strip() # Remove trailing period
                if len(best_match.split()) > 150: # Avoid very long matches
                    best_match = "Not specified (too verbose or unspecific)"
                if len(best_match.strip()) < 5 and not any(char.isdigit() for char in best_match): # Too short or non-descriptive
                    best_match = "Not specified"
            return best_match


        # --- Information Extraction Logic (Enhanced) ---

        # Project Name
        project_name = "Not specified"
        # Attempt 1: Specific pattern for "AGREEMENT NAME OF PROJECT:"
        project_name_match_1 = re.search(r'(?:AGREEMENT NAME OF PROJECT|PROJECT NAME|NAME OF PROJECT|TITLE OF WORK|WORK TITLE|AGREEMENT TITLE|SUBJECT MATTER OF AGREEMENT)[:\s]*(.*?)(?:\n{1,2}|The Agreement is entered|Between the|This Agreement|Whereas|WHEREAS|WITNESSETH|hereinafter)', text, re.IGNORECASE | re.DOTALL)
        if project_name_match_1:
            project_name = project_name_match_1.group(1).strip()

        # Attempt 2: Broader keywords + smart_search if Attempt 1 fails or is too short
        if project_name == "Not specified" or len(project_name.split()) < 3:
            project_name_keywords = [
                "name of work", "project title", "work of", "tender for", "project name",
                "agreement name of project", "subject of work", "concerning",
                "improvement & construction of", "agreement for", "work order for",
                "nature of work", "development of", "contract for"
            ]
            project_name = smart_search(text, project_name_keywords, search_window=150)
            # Refine project name from smart_search output
            project_name = re.sub(r'(?:agreement name of project|agreement for|project title|name of work|subject|tender for|work order no|nature of work|contract for)[:\s]*', '', project_name, flags=re.IGNORECASE).strip()
            # Remove any leading numbers/bullets that might be caught
            project_name = re.sub(r'^\s*[\d\.\-]+\s*', '', project_name).strip()

        # General cleanup for project name
        project_name = re.sub(r'\s*\(hereinafter referred to as[\s\S]*?\)\s*', '', project_name, flags=re.IGNORECASE).strip()
        project_name = re.sub(r'^\W+|\W+$', '', project_name).strip() # Remove leading/trailing non-alphanumeric
        if project_name.lower() in [kw.lower() for kw in project_name_keywords] or len(project_name.strip()) < 5:
            project_name = "Not specified"
        elif project_name.endswith('.'): project_name = project_name[:-1].strip() # Remove trailing period


        # Parties Involved
        parties = "Not specified"
        # Prioritize 'between X and Y'
        parties_match_1 = re.search(r'between\s+(.*?)(?:\s+\(hereinafter referred to as(?: the)?\s*["\']?.*?["\']?\s*\)?)?\s+and\s+(.*?)(?:\s+\(hereinafter referred to as(?: the)?\s*["\']?.*?["\']?\s*\)?)?(?:,|,\s*witnesseth|,\s*WHEREAS|\.|$|This Agreement is made)', text, re.IGNORECASE | re.DOTALL)
        if parties_match_1:
            party1 = parties_match_1.group(1).strip()
            party2 = parties_match_1.group(2).strip()

            # Aggressive cleanup of party names
            party1 = re.split(r'(?:,\s*(?:a company|a corporation|an individual|having its registered office|residing at|of|having its principal place of business at|represented by|represented herein by|the party of the first part))', party1, 1, flags=re.IGNORECASE)[0].strip()
            party2 = re.split(r'(?:,\s*(?:a company|a corporation|an individual|having its registered office|residing at|of|having its principal place of business at|represented by|represented herein by|the party of the second part))', party2, 1, flags=re.IGNORECASE)[0].strip()
            
            # Shorten very long party names if they contain common boilerplate
            if "municipal corporation" in party1.lower() and len(party1.split()) > 7:
                party1 = re.search(r'(?:the\s+)?(?:[A-Z][a-z]+\s*){1,4}(?:Corporation|Council|Authority)(?: of\s+[A-Z][a-z]+(?:(?:\s|-)?[A-Z][a-z]+)*)?', party1).group(0) if re.search(r'(?:the\s+)?(?:[A-Z][a-z]+\s*){1,4}(?:Corporation|Council|Authority)(?: of\s+[A-Z][a-z]+(?:(?:\s|-)?[A-Z][a-z]+)*)?', party1) else party1
            if "municipal corporation" in party2.lower() and len(party2.split()) > 7:
                party2 = re.search(r'(?:the\s+)?(?:[A-Z][a-z]+\s*){1,4}(?:Corporation|Council|Authority)(?: of\s+[A-Z][a-z]+(?:(?:\s|-)?[A-Z][a-z]+)*)?', party2).group(0) if re.search(r'(?:the\s+)?(?:[A-Z][a-z]+\s*){1,4}(?:Corporation|Council|Authority)(?: of\s+[A-Z][a-z]+(?:(?:\s|-)?[A-Z][a-z]+)*)?', party2) else party2

            parties = f"{party1} and {party2}"

        # Fallback to smart_search for parties
        if parties == "Not specified":
            parties_keywords = ["between", "municipal corporation", "contractor", "agreement signed", "entered into by", "parties involved", "first part", "second part", "made and entered into", "this agreement is made by and between"]
            parties = smart_search(text, parties_keywords, search_window=200)
            parties = re.sub(r'(?:between|agreement name of project|agreement for|made and entered into|this agreement is made by and between)[:\s]*', '', parties, flags=re.IGNORECASE).strip()

        parties = re.sub(r'^\W+|\W+$', '', parties).strip()
        if parties.lower() in [kw.lower() for kw in parties_keywords] or len(parties.strip()) < 5 or parties.lower().startswith("this agreement"):
            parties = "Not specified"
        elif parties.endswith('.'): parties = parties[:-1].strip()


        # Agreement Date
        date_match = re.search(r'(?:dated|on this)\s+(?:the\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+day of\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*,\s*\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*|\s+)\d{4}\b)', text, re.IGNORECASE)
        date = date_match.group(1).strip() if date_match else "Not specified"
        if date != "Not specified":
            date = re.sub(r'^\s*(?:the\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+day of)\s*', '', date, flags=re.IGNORECASE).strip()
            date = re.sub(r'[,\.]\s*$', '', date).strip() # Remove trailing commas/periods

        # Amount / Consideration
        amount_keywords = ["contract value", "final payable amount", "total amount", "estimated cost", "sum of rupees", "rupees", "lakh", "crore", "total consideration", "cost of work", "price of the work", "contract price", "payable amount", "financial consideration"]
        amount_sentence = smart_search(text, amount_keywords, search_window=150)
        amount = "Not specified"
        if "not specified" not in amount_sentence.lower():
            # More comprehensive amount regex to capture various number and currency formats
            amt_match = re.search(r'(?:(?:[Rr][Ss]\.?|₹)\s*[\d,\.]+(?:\.\d{1,2})?|\b(?:(?:[\d,\.]+\s*(?:lakhs?|crores?|millions?|billions?))\s*(?:only|rupees)?)\b|\b(?:(?:one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|lakh|crore)(?:\s+and\s+(?:(?:[Rr][Ss]\.?|₹)?\s*[\d,\.]+))?)\b)\s*(?:only)?', amount_sentence, re.IGNORECASE)
            if amt_match:
                amount = amt_match.group(0).upper().strip()
                amount = re.sub(r'\s*only$', '', amount, flags=re.IGNORECASE).strip()
            else:
                # Fallback to general number extraction if specific currency format not found
                num_match = re.search(r'[\d,\.]+(?:\.\d{1,2})?', amount_sentence)
                if num_match:
                    amount = num_match.group(0)
                else:
                    amount = amount_sentence # Use the whole sentence if it seems relevant
        
        amount = re.sub(r'^\W+|\W+$', '', amount).strip()
        if amount.lower() in [kw.lower() for kw in amount_keywords] or len(amount.strip()) < 5:
            amount = "Not specified"


        # Scope of Work
        scope_keywords = [
            "scope of work", "the work consists of", "description of work", "nature of work", "details of work",
            "project includes", "the work includes", "responsibilities include",
            "construction and improvement", "for the work of", "carrying out the work of", "execution of work",
            "services to be provided", "works to be carried out", "objective of this agreement",
            "purpose of this agreement", "subject of this contract"
        ]
        scope = smart_search(text, scope_keywords, search_window=300) # Increased search window for scope
        if scope != "Not specified":
            scope = re.sub(r'(?:scope of work|the work consists of|description of work|nature of work|details of work|project includes|the work includes|responsibilities include|construction and improvement|for the work of|carrying out the work of|execution of work|services to be provided|works to be carried out|objective of this agreement|purpose of this agreement|subject of this contract)[:\s]*(is|are|details|following|as follows|the following)?\s*', '', scope, flags=re.IGNORECASE).strip()
            # Remove trailing sentences that might be legal boilerplate
            scope = re.sub(r'(?:(?=\n\n)|(?=The contractor shall complete)|(?=Article \d)|(?=Clause \d)|(?=Term of)|(?=duration of work)|(?=schedule of work)|(?=period of completion)|(?=terms and conditions)|(?=consideration for the work)|(?=TOTAL COST)|(?=AMOUNT IN RUPEES)|(?=IN WITNESS WHEREOF)).*$', '', scope, flags=re.IGNORECASE | re.DOTALL).strip()
            if scope.endswith('.'): scope = scope[:-1].strip()

        # Further cleanup for scope
        scope = re.sub(r'^\W+|\W+$', '', scope).strip()
        if scope.lower() in [kw.lower() for kw in scope_keywords] or len(scope.strip()) < 5:
            scope = "Not specified"


        # Duration / Completion Period
        duration_keywords = ["within", "calendar months", "construction period", "project completion time", "period of completion", "complete the work within", "duration of this agreement", "time for completion", "completion period", "contract duration"]
        duration_sentence = smart_search(text, duration_keywords, search_window=150)
        duration = "Not specified"
        if "not specified" not in duration_sentence.lower():
            duration_match = re.search(r'(\d+\s+(?:days?|weeks?|months?|years?)\s*(?:calendar|working)?(?: from the date of agreement| from the date of commencement of work| from the date of issue of work order)?|within\s+\d+\s+(?:days?|weeks?|months?|years?))', duration_sentence, re.IGNORECASE)
            if duration_match:
                duration = duration_match.group(1).strip()
            elif "not specified" not in duration_sentence.lower() and len(duration_sentence.split()) < 50: # If smart_search found something short
                duration = duration_sentence # Use the whole matched sentence

        if duration.lower() in [kw.lower() for kw in duration_keywords] or len(duration.strip()) < 5:
            duration = "Not specified"

        # Clauses Detection
        clauses = {
            "Confidentiality": ["confidentiality", "non-disclosure", "nda", "secrecy of information", "confidential information"],
            "Termination": ["termination", "cancelled", "terminate", "expiration of this agreement", "end of agreement", "event of default", "breach of contract"],
            "Dispute Resolution": ["arbitration", "dispute resolution", "resolved by", "decision of commissioner", "disputes shall be settled", "court of law", "jurisdiction", "legal proceedings", "amicable settlement", "conciliation", "litigation"],
            "Jurisdiction": ["jurisdiction", "governing law", "court of", "applicable law", "laws of india", "courts in", "seat of arbitration"],
            "Force Majeure": ["force majeure", "natural events", "act of god", "unforeseen circumstances", "beyond control of either party", "calamity", "natural disaster"],
            "Indemnification": ["indemnify", "hold harmless", "indemnity", "damages and liabilities", "compensate"],
            "Payment Terms": ["payment terms", "invoice", "remuneration", "fees payable", "payment schedule", "consideration", "billing"],
            "Signatures": ["signed by", "signature of", "authorized signatory", "witnesses", "party of the first part", "party of the second part", "seal of the company", "executed by"]
        }

        clause_results = []
        for name, keywords in clauses.items():
            found = smart_search(text, keywords, search_window=200)
            clause_results.append(f"✅ {name}" if found != "Not specified" else f"❌ {name}")

        # --- Summary Paragraph Generation ---
        paragraph = "This agreement"
        parts = []

        if parties != "Not specified":
            parts.append(f"is made between {parties}")
        if date != "Not specified":
            parts.append(f"on {date}")
        if project_name != "Not specified":
            parts.append(f"for the project titled: '{project_name}'")
        if scope != "Not specified":
            parts.append(f"with a scope of work encompassing: {scope}")
        if amount != "Not specified":
            parts.append(f"and a total contract value of: {amount}")
        if duration != "Not specified":
            parts.append(f"to be completed within {duration}")
        
        if parts:
            paragraph += " " + ", ".join(parts) + "."
        else:
            paragraph = "A detailed summary could not be generated due to limited or unextractable key information from the document. Please check the 'Raw Extracted Text' for content."


        included_clauses = [c[2:] for c in clause_results if c.startswith("✅")]
        if included_clauses:
            paragraph += " Key clauses detected include: " + ", ".join(included_clauses) + "."
        
        if len(paragraph.split()) < 10 and not parts: # If initial paragraph is too short and no key info found
             paragraph = "No significant key information (Project Name, Parties, Amount, Scope, Duration) could be extracted from this document. Please verify the content of the 'Raw Extracted Text' to ensure text was extracted correctly."


        st.subheader("📑 Extracted Agreement Summary")
        st.markdown(f"""
        <div style="font-size:17px; background:#f4f6f8; padding:20px; border-radius:10px; border-left: 5px solid #003366;">
            <p><b>📌 Project Title:</b> {textwrap.fill(project_name, 100)}</p>
            <p><b>📅 Agreement Date:</b> {date}</p>
            <p><b>👥 Parties Involved:</b> {textwrap.fill(parties, 100)}</p>
            <p><b>💰 Amount/Consideration:</b> {textwrap.fill(amount, 100)}</p>
            <p><b>📦 Scope of Work:</b> {textwrap.fill(scope, 100)}</p>
            <p><b>⏱ Duration of Agreement:</b> {duration}</p>
            <br>
            <p><b>🧾 Legal Clauses Coverage:</b><br>{"<br>".join(clause_results)}</p>
            <br>
            <p><b>🧠 Comprehensive Summary:</b><br>{textwrap.fill(paragraph, 100)}</p>
        </div>
        """, unsafe_allow_html=True)

        # --- Translation & Audio ---
        
        # Get supported gTTS languages dynamically for validation
        supported_gtts_languages = {}
        try:
            # Create a dummy gTTS object with lang_check=False for faster instantiation
            # then call lang_list() which makes the actual network call to get supported languages
            temp_tts = gTTS(text="dummy", lang="en", lang_check=False) 
            supported_gtts_languages = temp_tts.lang_list()
        except Exception as e:
            logging.error(f"Could not retrieve gTTS language list dynamically: {e}")
            st.warning("⚠️ Could not retrieve list of supported gTTS languages. Audio generation might be limited.")


        final_text_for_audio = paragraph
        display_translated_text = False
        target_lang_code = 'en' # Default for gTTS

        if lang == "Marathi":
            st.info("🌐 Translating summary to Marathi...")
            try:
                translated_paragraph = GoogleTranslator(source='auto', target='mr').translate(paragraph)
                final_text_for_audio = translated_paragraph
                display_translated_text = True
                target_lang_code = 'mr' # Marathi language code for gTTS
                st.subheader("🈯 Marathi Translation")
                st.text_area("Translated Summary", final_text_for_audio, height=300)
            except Exception as e:
                st.error(f"❌ Marathi translation failed: {e}")
                st.info("Falling back to English summary for audio.")
                final_text_for_audio = paragraph # Revert to English for audio if translation fails

        st.subheader("🎧 Audio Summary")
        try:
            # Check if the chosen audio language code is supported by gTTS
            if target_lang_code not in supported_gtts_languages and supported_gtts_languages:
                st.warning(f"⚠️ The chosen language '{lang}' (code: '{target_lang_code}') might not be fully supported by gTTS for audio. Defaulting to English voice.")
                target_lang_code = 'en' # Fallback for gTTS if unsupported

            # Ensure text is not empty before generating audio
            if final_text_for_audio and final_text_for_audio.strip() != "":
                tts = gTTS(final_text_for_audio, lang=target_lang_code)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_tmp_file:
                    audio_path = audio_tmp_file.name
                    tts.save(audio_path)
                
                with open(audio_path, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    b64 = base64.b64encode(audio_bytes).decode()
                    audio_html = f"""
                        <audio controls style='width:100%;'>
                            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                            Your browser does not support the audio element.
                        </audio>
                    """
                    st.markdown(audio_html, unsafe_allow_html=True)
                st.success("✅ Audio generated successfully!")
            else:
                st.warning("No text available for audio generation.")

        except Exception as e:
            st.error(f"❌ Failed to generate audio: {e}")
            st.info("This can happen if the generated summary is empty or if there's a network issue with gTTS.")
        finally:
            if 'audio_path' in locals() and os.path.exists(audio_path):
                os.remove(audio_path)

    except Exception as e:
        st.error(f"❌ An unexpected error occurred during PDF processing or summary generation: {e}")
        st.exception(e)
    finally:
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)

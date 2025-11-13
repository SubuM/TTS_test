import streamlit as st
import pytesseract
from PIL import Image
import pdf2image
import tempfile
import os
from io import BytesIO
import langdetect
from deep_translator import GoogleTranslator

# Page configuration
st.set_page_config(
    page_title="OCR Text Extractor with Translation",
    page_icon="📄",
    layout="centered"
)

st.title("📄 OCR Text Extractor with Translation")
st.markdown("Extract text from images and PDFs, then translate to your preferred language")
st.markdown("---")

# Tesseract language codes mapping (comprehensive list)
LANGUAGES = {
    "Afrikaans": "afr",
    "Albanian": "sqi",
    "Amharic": "amh",
    "Arabic": "ara",
    "Armenian": "hye",
    "Assamese": "asm",
    "Azerbaijani": "aze",
    "Basque": "eus",
    "Belarusian": "bel",
    "Bengali": "ben",
    "Bosnian": "bos",
    "Bulgarian": "bul",
    "Burmese": "mya",
    "Catalan": "cat",
    "Cebuano": "ceb",
    "Chinese (Simplified)": "chi_sim",
    "Chinese (Traditional)": "chi_tra",
    "Croatian": "hrv",
    "Czech": "ces",
    "Danish": "dan",
    "Dutch": "nld",
    "English": "eng",
    "Esperanto": "epo",
    "Estonian": "est",
    "Finnish": "fin",
    "French": "fra",
    "Galician": "glg",
    "Georgian": "kat",
    "German": "deu",
    "Greek": "ell",
    "Gujarati": "guj",
    "Haitian": "hat",
    "Hebrew": "heb",
    "Hindi": "hin",
    "Hungarian": "hun",
    "Icelandic": "isl",
    "Indonesian": "ind",
    "Irish": "gle",
    "Italian": "ita",
    "Japanese": "jpn",
    "Javanese": "jav",
    "Kannada": "kan",
    "Kazakh": "kaz",
    "Khmer": "khm",
    "Korean": "kor",
    "Kyrgyz": "kir",
    "Lao": "lao",
    "Latin": "lat",
    "Latvian": "lav",
    "Lithuanian": "lit",
    "Macedonian": "mkd",
    "Malay": "msa",
    "Malayalam": "mal",
    "Maltese": "mlt",
    "Marathi": "mar",
    "Mongolian": "mon",
    "Nepali": "nep",
    "Norwegian": "nor",
    "Oriya": "ori",
    "Pashto": "pus",
    "Persian": "fas",
    "Polish": "pol",
    "Portuguese": "por",
    "Punjabi": "pan",
    "Romanian": "ron",
    "Russian": "rus",
    "Sanskrit": "san",
    "Serbian": "srp",
    "Sinhala": "sin",
    "Slovak": "slk",
    "Slovenian": "slv",
    "Spanish": "spa",
    "Swahili": "swa",
    "Swedish": "swe",
    "Syriac": "syr",
    "Tagalog": "tgl",
    "Tajik": "tgk",
    "Tamil": "tam",
    "Telugu": "tel",
    "Thai": "tha",
    "Tibetan": "bod",
    "Turkish": "tur",
    "Ukrainian": "ukr",
    "Urdu": "urd",
    "Uzbek": "uzb",
    "Vietnamese": "vie",
    "Welsh": "cym",
    "Yiddish": "yid",
}

# Translation language codes (Google Translate format)
TRANSLATION_LANGUAGES = {
    "No Translation": None,
    "English": "en",
    "German": "de",
    "Spanish": "es",
    "French": "fr",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Russian": "ru",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW",
    "Arabic": "ar",
    "Hindi": "hi",
    "Turkish": "tr",
    "Polish": "pl",
    "Czech": "cs",
    "Greek": "el",
    "Hebrew": "he",
    "Thai": "th",
    "Vietnamese": "vi",
    "Indonesian": "id",
    "Malay": "ms",
    "Filipino": "fil",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Romanian": "ro",
    "Bulgarian": "bg",
    "Croatian": "hr",
    "Serbian": "sr",
    "Ukrainian": "uk",
    "Persian": "fa",
    "Urdu": "ur",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te",
}

# Language detection mapping (ISO codes to language names)
LANG_DETECT_MAP = {
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "ja": "Japanese",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "cs": "Czech",
    "el": "Greek",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
}

def detect_language_advanced(text):
    """Detect language with better mapping to Tesseract codes"""
    try:
        detected_lang = langdetect.detect(text)
        
        # Map langdetect codes to Tesseract language names
        lang_map = {
            "en": "English",
            "de": "German",
            "es": "Spanish",
            "fr": "French",
            "it": "Italian",
            "pt": "Portuguese",
            "nl": "Dutch",
            "ru": "Russian",
            "ja": "Japanese",
            "zh-cn": "Chinese (Simplified)",
            "zh-tw": "Chinese (Traditional)",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
            "tr": "Turkish",
            "pl": "Polish",
            "cs": "Czech",
            "el": "Greek",
            "he": "Hebrew",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "ro": "Romanian",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sr": "Serbian",
            "uk": "Ukrainian",
            "fa": "Persian",
            "ur": "Urdu",
            "bn": "Bengali",
            "ta": "Tamil",
            "te": "Telugu",
        }
        
        lang_name = lang_map.get(detected_lang, "English")
        return lang_name, detected_lang
    except:
        return "English", "en"

def auto_detect_and_extract(image_or_path, is_path=False):
    """Try to detect language and extract text with best results"""
    # Try with common languages first for better detection
    priority_languages = ["eng", "deu", "spa", "fra", "ita", "por", "rus", "jpn", "chi_sim", "ara"]
    
    best_text = ""
    best_lang = "eng"
    best_confidence = 0
    
    for lang_code in priority_languages:
        try:
            if is_path:
                # For PDF processing
                text = pytesseract.image_to_string(image_or_path, lang=lang_code, config='--oem 3 --psm 3')
            else:
                # For image processing
                text = pytesseract.image_to_string(image_or_path, lang=lang_code, config='--oem 3 --psm 3')
            
            # Check if we got meaningful text
            if len(text.strip()) > len(best_text.strip()):
                # Try to detect language from extracted text
                if len(text.strip()) > 20:
                    try:
                        detected_lang_code = langdetect.detect(text)
                        # If detected language matches what we tried, it's probably correct
                        best_text = text.strip()
                        best_lang = lang_code
                        break
                    except:
                        if len(text.strip()) > len(best_text.strip()):
                            best_text = text.strip()
                            best_lang = lang_code
        except:
            continue
    
    # If still no good results, try with English
    if not best_text:
        best_text = pytesseract.image_to_string(image_or_path, lang="eng", config='--oem 3 --psm 3').strip()
        best_lang = "eng"
    
    return best_text, best_lang

def translate_text(text, target_lang):
    """Translate text to target language using Google Translate"""
    try:
        # Split text into chunks if too long (Google Translate has limits)
        max_length = 4500
        if len(text) <= max_length:
            translator = GoogleTranslator(source='auto', target=target_lang)
            return translator.translate(text)
        else:
            # Split by paragraphs and translate in chunks
            paragraphs = text.split('\n\n')
            translated_paragraphs = []
            current_chunk = ""
            
            for para in paragraphs:
                if len(current_chunk) + len(para) < max_length:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        translator = GoogleTranslator(source='auto', target=target_lang)
                        translated_paragraphs.append(translator.translate(current_chunk))
                    current_chunk = para + "\n\n"
            
            # Translate remaining chunk
            if current_chunk:
                translator = GoogleTranslator(source='auto', target=target_lang)
                translated_paragraphs.append(translator.translate(current_chunk))
            
            return "\n\n".join(translated_paragraphs)
    except Exception as e:
        raise Exception(f"Translation error: {str(e)}")

def extract_text_from_image(image, language_code):
    """Extract text from PIL Image using Tesseract OCR"""
    try:
        # Configure Tesseract with selected language
        custom_config = f'--oem 3 --psm 3'
        text = pytesseract.image_to_string(image, lang=language_code, config=custom_config)
        return text.strip()
    except Exception as e:
        raise Exception(f"OCR Error: {str(e)}")

def extract_text_from_pdf(pdf_file, language_code):
    """Extract text from PDF file"""
    tmp_path = None
    try:
        # Save PDF to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.read())
            tmp_path = tmp_file.name
        
        # Convert PDF to images
        try:
            images = pdf2image.convert_from_path(tmp_path, dpi=300)
        except Exception as e:
            if "poppler" in str(e).lower():
                raise Exception(
                    "Poppler is not installed or not in PATH. "
                    "Please install poppler-utils:\n"
                    "- Ubuntu/Debian: sudo apt-get install poppler-utils\n"
                    "- macOS: brew install poppler\n"
                    "- Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/\n"
                    "For Streamlit Cloud: Add 'poppler-utils' to packages.txt"
                )
            else:
                raise e
        
        # Extract text from each page
        all_text = []
        for i, image in enumerate(images):
            st.info(f"Processing page {i+1} of {len(images)}...")
            text = extract_text_from_image(image, language_code)
            if text:
                all_text.append(f"--- Page {i+1} ---\n{text}")
        
        return "\n\n".join(all_text)
    
    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

# Language selection
st.markdown("### Settings")

col1, col2 = st.columns(2)

with col1:
    detection_mode = st.radio(
        "Source Language Detection:",
        options=["Auto-detect (Recommended)", "Manual Selection"],
        index=0,
        help="Auto-detect will try multiple languages for best OCR results"
    )

with col2:
    translation_language = st.selectbox(
        "Translation Language (Target):",
        options=list(TRANSLATION_LANGUAGES.keys()),
        index=1,  # Default to English
        help="Select target language for translation (or 'No Translation' to keep original)"
    )

# Manual language selection (only shown if Manual mode is selected)
manual_ocr_language = None
if detection_mode == "Manual Selection":
    sorted_languages = sorted(LANGUAGES.keys())
    default_index = sorted_languages.index("English")
    
    manual_ocr_language = st.selectbox(
        "Select OCR Language:",
        options=sorted_languages,
        index=default_index,
        help="Manually select the language of the text in your document"
    )

translation_lang_code = TRANSLATION_LANGUAGES[translation_language]

# Info box explaining the workflow
if detection_mode == "Auto-detect (Recommended)":
    if translation_lang_code:
        st.info(f"📋 Workflow: Auto-detect source language → Extract text → Translate to **{translation_language}**")
    else:
        st.info(f"📋 Workflow: Auto-detect source language → Extract text (no translation)")
else:
    if translation_lang_code:
        st.info(f"📋 Workflow: Extract text in **{manual_ocr_language}** → Translate to **{translation_language}**")
    else:
        st.info(f"📋 Workflow: Extract text in **{manual_ocr_language}** (no translation)")

# Additional options
st.markdown("### Advanced Options")
col3, col4 = st.columns(2)

with col3:
    auto_detect = st.checkbox("Auto-detect language after extraction", value=True)

with col4:
    show_confidence = st.checkbox("Show OCR confidence scores", value=False)

# File uploader
st.markdown("### Upload File")
st.info("📝 Supported formats: JPEG, JPG, PNG, PDF")

uploaded_file = st.file_uploader(
    "Choose an image or PDF file:",
    type=['jpg', 'jpeg', 'png', 'pdf'],
    label_visibility="collapsed"
)

if uploaded_file is not None:
    file_type = uploaded_file.name.split('.')[-1].lower()
    st.success(f"✅ File uploaded: **{uploaded_file.name}** ({uploaded_file.size / 1024:.2f} KB)")
    
    # Display preview for images
    if file_type in ['jpg', 'jpeg', 'png']:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)
        uploaded_file.seek(0)  # Reset file pointer
    else:
        st.info("📄 PDF file uploaded - preview not available")
    
    # Extract text button
    if st.button("🔍 Extract & Translate Text", type="primary"):
        
        # Determine which OCR approach to use
        if detection_mode == "Auto-detect (Recommended)":
            with st.spinner("Auto-detecting language and extracting text..."):
                try:
                    # Extract text based on file type with auto-detection
                    if file_type in ['jpg', 'jpeg', 'png']:
                        image = Image.open(uploaded_file)
                        extracted_text, detected_lang_code = auto_detect_and_extract(image, is_path=False)
                    elif file_type == 'pdf':
                        # For PDF, process first page to detect language, then use that for all pages
                        tmp_path = None
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                                tmp_file.write(uploaded_file.read())
                                tmp_path = tmp_file.name
                            
                            try:
                                images = pdf2image.convert_from_path(tmp_path, dpi=300)
                            except Exception as e:
                                if "poppler" in str(e).lower():
                                    raise Exception("Poppler is not installed. Add 'poppler-utils' to packages.txt for Streamlit Cloud")
                                else:
                                    raise e
                            
                            if images:
                                # Detect language from first page
                                st.info("Detecting language from first page...")
                                first_page_text, detected_lang_code = auto_detect_and_extract(images[0], is_path=False)
                                
                                # Now extract all pages with detected language
                                all_text = []
                                for i, image in enumerate(images):
                                    st.info(f"Processing page {i+1} of {len(images)}...")
                                    text = extract_text_from_image(image, detected_lang_code)
                                    if text:
                                        all_text.append(f"--- Page {i+1} ---\n{text}")
                                
                                extracted_text = "\n\n".join(all_text)
                            else:
                                raise Exception("No pages found in PDF")
                            
                        finally:
                            if tmp_path and os.path.exists(tmp_path):
                                try:
                                    os.unlink(tmp_path)
                                except:
                                    pass
                    else:
                        st.error("Unsupported file format")
                        st.stop()
                    
                    if extracted_text:
                        # Map detected code to language name
                        lang_code_to_name = {v: k for k, v in LANGUAGES.items()}
                        detected_language = lang_code_to_name.get(detected_lang_code, "Unknown")
                        
                        st.success(f"✅ Text extraction complete! Detected language: **{detected_language}**")
                        
                except Exception as e:
                    st.error(f"❌ Error during text extraction: {str(e)}")
                    st.stop()
        else:
            # Manual mode
            ocr_lang_code = LANGUAGES[manual_ocr_language]
            detected_language = manual_ocr_language
            
            with st.spinner(f"Extracting text using {manual_ocr_language} OCR..."):
                try:
                    # Extract text based on file type
                    if file_type in ['jpg', 'jpeg', 'png']:
                        image = Image.open(uploaded_file)
                        extracted_text = extract_text_from_image(image, ocr_lang_code)
                    elif file_type == 'pdf':
                        extracted_text = extract_text_from_pdf(uploaded_file, ocr_lang_code)
                    else:
                        st.error("Unsupported file format")
                        st.stop()
                    
                    if extracted_text:
                        st.success("✅ Text extraction complete!")
                    
                except Exception as e:
                    st.error(f"❌ Error during text extraction: {str(e)}")
                    st.stop()
        
        # Continue with common processing for both modes
        if extracted_text:
            
            # Show confidence scores if enabled
            if show_confidence:
                try:
                    if file_type in ['jpg', 'jpeg', 'png']:
                        image = Image.open(uploaded_file)
                        uploaded_file.seek(0)
                        ocr_code = detected_lang_code if detection_mode == "Auto-detect (Recommended)" else ocr_lang_code
                        data = pytesseract.image_to_data(image, lang=ocr_code, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                        if confidences:
                            avg_confidence = sum(confidences) / len(confidences)
                            st.metric("Average OCR Confidence", f"{avg_confidence:.1f}%")
                except:
                    pass
            
            # Display extracted text
            st.markdown(f"### 📄 Extracted Text ({detected_language}):")
            st.text_area(
                "Original:",
                extracted_text,
                height=200,
                label_visibility="collapsed",
                key="original_text"
            )
            
            # Character and word count
            char_count = len(extracted_text)
            word_count = len(extracted_text.split())
            st.caption(f"Characters: {char_count} | Words: {word_count}")
            
            # Translate if target language is selected
            translated_text = None
            if translation_lang_code:
                with st.spinner(f"Translating to {translation_language}..."):
                    try:
                        translated_text = translate_text(extracted_text, translation_lang_code)
                        st.success(f"✅ Translation to {translation_language} complete!")
                        
                        st.markdown(f"### 🌐 Translated Text ({translation_language}):")
                        st.text_area(
                            "Translated:",
                            translated_text,
                            height=200,
                            label_visibility="collapsed",
                            key="translated_text"
                        )
                        
                        # Character and word count for translation
                        trans_char_count = len(translated_text)
                        trans_word_count = len(translated_text.split())
                        st.caption(f"Characters: {trans_char_count} | Words: {trans_word_count}")
                        
                    except Exception as e:
                        st.error(f"❌ Translation error: {str(e)}")
                        st.info("💡 Translation failed, but you can still download the original extracted text below.")
            
            # Download buttons
            st.markdown("### 📥 Download Options")
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                # Prepare output filename for original
                base_name = uploaded_file.name.rsplit('.', 1)[0]
                original_filename = f"{base_name}_extracted_{detected_language.lower().replace(' ', '_')}.txt"
                
                # Create text file for download
                original_bytes = extracted_text.encode('utf-8')
                
                st.download_button(
                    label=f"📄 Download Original ({detected_language})",
                    data=original_bytes,
                    file_name=original_filename,
                    mime="text/plain",
                    key="download_original"
                )
            
            with col_dl2:
                if translated_text:
                    # Prepare output filename for translation
                    translated_filename = f"{base_name}_translated_{translation_language.lower().replace(' ', '_')}.txt"
                    
                    # Create text file for download
                    translated_bytes = translated_text.encode('utf-8')
                    
                    st.download_button(
                        label=f"🌐 Download Translated ({translation_language})",
                        data=translated_bytes,
                        file_name=translated_filename,
                        mime="text/plain",
                        key="download_translated"
                    )
            
        else:
            st.warning("⚠️ No text found in the document. Try using manual language selection or check image quality.")

else:
    st.info("👆 Please upload an image or PDF file to begin text extraction")

st.markdown("---")
st.markdown("### 📝 How It Works:")
st.markdown("""
**Auto-detect Mode (Recommended):**
1. Upload your document (image or PDF)
2. App automatically detects the source language
3. Extracts text using the detected language
4. Translates to your selected target language (if chosen)

**Manual Mode:**
- Use this if auto-detection fails or you know the exact source language
- Manually select the OCR language for extraction

**Example Workflow:**
- Upload a German PDF → App detects "German" → Translate to "English"
- Result: German text extracted and translated to English ✅

**Tips for best results:**
- Use high-quality, clear images (300 DPI or higher)
- Ensure good contrast between text and background
- Auto-detect works best with clear, well-formatted text
- Use Manual mode for documents with poor quality or mixed languages
""")

st.markdown("---")
st.caption("Powered by Tesseract OCR, Google Translate & deep-translator | No data stored | All processing in-memory")
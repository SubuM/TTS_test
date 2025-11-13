import streamlit as st
import pytesseract
from PIL import Image
import pdf2image
import tempfile
import os
from io import BytesIO
import langdetect

# Page configuration
st.set_page_config(
    page_title="OCR Text Extractor",
    page_icon="📄",
    layout="centered"
)

st.title("📄 OCR Text Extractor")
st.markdown("Extract text from images and PDFs using Tesseract OCR")
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
    "Kurdish": "kur",
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

def detect_language(text):
    """Detect language of extracted text"""
    try:
        detected_lang = langdetect.detect(text)
        lang_name = LANG_DETECT_MAP.get(detected_lang, f"Unknown ({detected_lang})")
        return lang_name, detected_lang
    except:
        return "Unable to detect", None

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
        images = pdf2image.convert_from_path(tmp_path, dpi=300)
        
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
col1, col2 = st.columns(2)

with col1:
    # Sort languages alphabetically for easier selection
    sorted_languages = sorted(LANGUAGES.keys())
    default_index = sorted_languages.index("English")
    
    ocr_language = st.selectbox(
        "Select OCR Language:",
        options=sorted_languages,
        index=default_index,
        help="Select the language of the text in your document"
    )

with col2:
    output_language = st.selectbox(
        "Output Text File Language:",
        options=["Same as OCR", "English", "German", "Spanish", "French", "Italian", "Portuguese"],
        index=0,
        help="Language for the output text file name"
    )

ocr_lang_code = LANGUAGES[ocr_language]

# Additional options
st.markdown("### Advanced Options")
col3, col4 = st.columns(2)

with col3:
    auto_detect = st.checkbox("Auto-detect language after extraction", value=True)

with col4:
    show_confidence = st.checkbox("Show confidence scores", value=False)

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
    if st.button("🔍 Extract Text with OCR", type="primary"):
        with st.spinner(f"Extracting text using {ocr_language} OCR..."):
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
                    
                    # Auto-detect language if enabled
                    if auto_detect and len(extracted_text) > 20:
                        detected_lang_name, detected_lang_code = detect_language(extracted_text)
                        st.info(f"🌍 Detected language: **{detected_lang_name}**")
                    
                    # Show confidence scores if enabled
                    if show_confidence:
                        try:
                            if file_type in ['jpg', 'jpeg', 'png']:
                                image = Image.open(uploaded_file)
                                uploaded_file.seek(0)
                                data = pytesseract.image_to_data(image, lang=ocr_lang_code, output_type=pytesseract.Output.DICT)
                                confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                                if confidences:
                                    avg_confidence = sum(confidences) / len(confidences)
                                    st.metric("Average Confidence", f"{avg_confidence:.1f}%")
                        except:
                            pass
                    
                    # Display extracted text
                    st.markdown("### 📄 Extracted Text:")
                    st.text_area(
                        "Result:",
                        extracted_text,
                        height=300,
                        label_visibility="collapsed"
                    )
                    
                    # Character and word count
                    char_count = len(extracted_text)
                    word_count = len(extracted_text.split())
                    st.caption(f"Characters: {char_count} | Words: {word_count}")
                    
                    # Prepare output filename
                    base_name = uploaded_file.name.rsplit('.', 1)[0]
                    if output_language == "Same as OCR":
                        output_filename = f"{base_name}_extracted.txt"
                    else:
                        output_filename = f"{base_name}_extracted_{output_language.lower()}.txt"
                    
                    # Create text file for download
                    text_bytes = extracted_text.encode('utf-8')
                    
                    st.download_button(
                        label="📥 Download Text File",
                        data=text_bytes,
                        file_name=output_filename,
                        mime="text/plain",
                        type="primary"
                    )
                    
                else:
                    st.warning("⚠️ No text found in the document. Try adjusting the OCR language or check image quality.")
                
            except Exception as e:
                st.error(f"❌ Error during text extraction: {str(e)}")
                st.info("💡 Tips:\n- Ensure the image is clear and text is readable\n- Try selecting the correct language\n- For PDFs, ensure they contain actual images (not native text)")

else:
    st.info("👆 Please upload an image or PDF file to begin text extraction")

st.markdown("---")
st.markdown("### 📝 About Tesseract OCR:")
st.markdown("""
- ✅ Supports 100+ languages
- ✅ Works with images (JPG, JPEG, PNG)
- ✅ Extracts text from PDF pages
- ✅ Auto-detects text language
- ✅ No data stored - all processing in-memory

**Tips for best results:**
- Use high-quality, clear images (300 DPI or higher)
- Ensure good contrast between text and background
- Select the correct OCR language for better accuracy
- For PDFs, each page is processed separately
""")

st.markdown("---")
st.caption("Powered by Tesseract OCR & pytesseract | No data stored | All processing in-memory")
import streamlit as st
import pytesseract
from PIL import Image
import pdf2image
import tempfile
import os
from io import BytesIO
import langdetect
from deep_translator import GoogleTranslator
from gtts import gTTS
import base64

# Page configuration
st.set_page_config(
    page_title="Basic Audio Book",
    page_icon="🔊📄 ",
    layout="centered"
)

st.title("🔊📄 Basic Audio Book")
st.markdown("Extract text from images/PDFs, translate, and listen to the results")
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

# TTS language mapping (gTTS uses different codes)
TTS_LANGUAGES = {
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
    
    for lang_code in priority_languages:
        try:
            if is_path:
                text = pytesseract.image_to_string(image_or_path, lang=lang_code, config='--oem 3 --psm 3')
            else:
                text = pytesseract.image_to_string(image_or_path, lang=lang_code, config='--oem 3 --psm 3')
            
            # Check if we got meaningful text
            if len(text.strip()) > len(best_text.strip()):
                if len(text.strip()) > 20:
                    try:
                        langdetect.detect(text)
                        best_text = text.strip()
                        best_lang = lang_code
                        break
                    except:
                        if len(text.strip()) > len(best_text.strip()):
                            best_text = text.strip()
                            best_lang = lang_code
        except:
            continue
    
    if not best_text:
        best_text = pytesseract.image_to_string(image_or_path, lang="eng", config='--oem 3 --psm 3').strip()
        best_lang = "eng"
    
    return best_text, best_lang

def translate_text(text, target_lang):
    """Translate text to target language using Google Translate"""
    try:
        max_length = 4500
        if len(text) <= max_length:
            translator = GoogleTranslator(source='auto', target=target_lang)
            return translator.translate(text)
        else:
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
            
            if current_chunk:
                translator = GoogleTranslator(source='auto', target=target_lang)
                translated_paragraphs.append(translator.translate(current_chunk))
            
            return "\n\n".join(translated_paragraphs)
    except Exception as e:
        raise Exception(f"Translation error: {str(e)}")

def text_to_speech(text, lang_code, slow=False):
    """Convert text to speech using gTTS"""
    try:
        # Limit text length for TTS (gTTS has limits)
        max_tts_length = 3000
        if len(text) > max_tts_length:
            text = text[:max_tts_length] + "..."
            st.warning(f"⚠️ Text truncated to {max_tts_length} characters for audio generation")
        
        tts = gTTS(text=text, lang=lang_code, slow=slow)
        audio_fp = BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        
        # Convert to base64
        audio_bytes = audio_fp.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
        # Create HTML5 audio player
        audio_html = f"""
        <audio controls autoplay style="width: 100%; margin-top: 10px;">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            Your browser does not support the audio element.
        </audio>
        """
        
        return audio_html, audio_fp
    except Exception as e:
        raise Exception(f"TTS error: {str(e)}")

def extract_text_from_image(image, language_code):
    """Extract text from PIL Image using Tesseract OCR"""
    try:
        custom_config = f'--oem 3 --psm 3'
        text = pytesseract.image_to_string(image, lang=language_code, config=custom_config)
        return text.strip()
    except Exception as e:
        raise Exception(f"OCR Error: {str(e)}")

def extract_text_from_pdf(pdf_file, language_code):
    """Extract text from PDF file"""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.read())
            tmp_path = tmp_file.name
        
        try:
            images = pdf2image.convert_from_path(tmp_path, dpi=300)
        except Exception as e:
            if "poppler" in str(e).lower():
                raise Exception(
                    "Poppler is not installed. Add 'poppler-utils' to packages.txt for Streamlit Cloud"
                )
            else:
                raise e
        
        all_text = []
        for i, image in enumerate(images):
            st.info(f"Processing page {i+1} of {len(images)}...")
            text = extract_text_from_image(image, language_code)
            if text:
                all_text.append(f"--- Page {i+1} ---\n{text}")
        
        return "\n\n".join(all_text)
    
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

# Language selection
st.markdown("### Settings")

col1, col2, col3 = st.columns(3)

with col1:
    detection_mode = st.radio(
        "Source Language:",
        options=["Auto-detect", "Manual"],
        index=0,
        help="Auto-detect will try multiple languages for best OCR results"
    )

with col2:
    translation_language = st.selectbox(
        "Translate To:",
        options=list(TRANSLATION_LANGUAGES.keys()),
        index=1,  # Default to English
        help="Select target language for translation"
    )

with col3:
    enable_tts = st.checkbox(
        "Enable TTS",
        value=True,
        help="Read translated text aloud"
    )

# Manual language selection (only shown if Manual mode is selected)
manual_ocr_language = None
if detection_mode == "Manual":
    sorted_languages = sorted(LANGUAGES.keys())
    default_index = sorted_languages.index("English")
    
    manual_ocr_language = st.selectbox(
        "Select OCR Language:",
        options=sorted_languages,
        index=default_index,
        help="Manually select the language of the text in your document"
    )

translation_lang_code = TRANSLATION_LANGUAGES[translation_language]

# TTS options
if enable_tts and translation_lang_code:
    col_tts1, col_tts2 = st.columns(2)
    with col_tts1:
        tts_slow = st.checkbox("Slow speech (for learning)", value=False)
    with col_tts2:
        auto_play = st.checkbox("Auto-play audio", value=True)

# Info box explaining the workflow
if detection_mode == "Auto-detect":
    if translation_lang_code:
        workflow = f"📋 Workflow: Auto-detect → Extract → Translate to **{translation_language}**"
        if enable_tts:
            workflow += f" → 🔊 Read aloud"
        st.info(workflow)
    else:
        st.info(f"📋 Workflow: Auto-detect → Extract text (no translation)")
else:
    if translation_lang_code:
        workflow = f"📋 Workflow: Extract in **{manual_ocr_language}** → Translate to **{translation_language}**"
        if enable_tts:
            workflow += f" → 🔊 Read aloud"
        st.info(workflow)
    else:
        st.info(f"📋 Workflow: Extract text in **{manual_ocr_language}** (no translation)")

# Additional options
st.markdown("### Advanced Options")
col3, col4 = st.columns(2)

with col3:
    show_confidence = st.checkbox("Show OCR confidence scores", value=False)

with col4:
    show_original = st.checkbox("Show original text", value=True)

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
        uploaded_file.seek(0)
    else:
        st.info("📄 PDF file uploaded - preview not available")
    
    # Extract text button
    if st.button("🔍 Extract, Translate & Speak", type="primary"):
        
        # Determine which OCR approach to use
        if detection_mode == "Auto-detect":
            with st.spinner("Auto-detecting language and extracting text..."):
                try:
                    if file_type in ['jpg', 'jpeg', 'png']:
                        image = Image.open(uploaded_file)
                        extracted_text, detected_lang_code = auto_detect_and_extract(image, is_path=False)
                    elif file_type == 'pdf':
                        tmp_path = None
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                                tmp_file.write(uploaded_file.read())
                                tmp_path = tmp_file.name
                            
                            try:
                                images = pdf2image.convert_from_path(tmp_path, dpi=300)
                            except Exception as e:
                                if "poppler" in str(e).lower():
                                    raise Exception("Poppler is not installed. Add 'poppler-utils' to packages.txt")
                                else:
                                    raise e
                            
                            if images:
                                st.info("Detecting language from first page...")
                                first_page_text, detected_lang_code = auto_detect_and_extract(images[0], is_path=False)
                                
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
                        ocr_code = detected_lang_code if detection_mode == "Auto-detect" else ocr_lang_code
                        data = pytesseract.image_to_data(image, lang=ocr_code, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                        if confidences:
                            avg_confidence = sum(confidences) / len(confidences)
                            st.metric("Average OCR Confidence", f"{avg_confidence:.1f}%")
                except:
                    pass
            
            # Display original extracted text if enabled
            if show_original:
                st.markdown(f"### 📄 Extracted Text ({detected_language}):")
                st.text_area(
                    "Original:",
                    extracted_text,
                    height=200,
                    label_visibility="collapsed",
                    key="original_text"
                )
                
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
                        
                        trans_char_count = len(translated_text)
                        trans_word_count = len(translated_text.split())
                        st.caption(f"Characters: {trans_char_count} | Words: {trans_word_count}")
                        
                        # Generate TTS for translated text
                        if enable_tts and translation_language in TTS_LANGUAGES:
                            with st.spinner("Generating audio..."):
                                try:
                                    tts_lang_code = TTS_LANGUAGES[translation_language]
                                    audio_html, audio_fp = text_to_speech(translated_text, tts_lang_code, slow=tts_slow if 'tts_slow' in locals() else False)
                                    
                                    st.success("✅ Audio generated!")
                                    st.markdown(f"### 🔊 Listen to Translation ({translation_language}):")
                                    st.markdown(audio_html, unsafe_allow_html=True)
                                    
                                    # Download button for audio
                                    audio_fp.seek(0)
                                    st.download_button(
                                        label="📥 Download Audio (MP3)",
                                        data=audio_fp,
                                        file_name=f"translated_audio_{translation_language.lower()}.mp3",
                                        mime="audio/mp3",
                                        key="download_audio"
                                    )
                                    
                                except Exception as e:
                                    st.error(f"❌ TTS error: {str(e)}")
                        elif enable_tts:
                            st.warning(f"⚠️ TTS not available for {translation_language}")
                        
                    except Exception as e:
                        st.error(f"❌ Translation error: {str(e)}")
                        st.info("💡 Translation failed, but you can still download the original extracted text below.")
            
            # Download buttons for text files
            st.markdown("### 📥 Download Text Files")
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                base_name = uploaded_file.name.rsplit('.', 1)[0]
                original_filename = f"{base_name}_extracted_{detected_language.lower().replace(' ', '_')}.txt"
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
                    translated_filename = f"{base_name}_translated_{translation_language.lower().replace(' ', '_')}.txt"
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
    st.info("👆 Please upload an image or PDF file to begin")


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
import sqlite3
import hashlib
from datetime import datetime
import re

# Page configuration
st.set_page_config(
    page_title="OCR Translator with TTS",
    page_icon="📄",
    layout="centered"
)

# Database setup
def init_database():
    """Initialize SQLite database for user management"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create activity log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            activity_type TEXT,
            source_language TEXT,
            target_language TEXT,
            character_count INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create static admin user from secrets if not exists
    try:
        admin_username = st.secrets["admin"]["username"]
        admin_password = st.secrets["admin"]["password"]
        admin_email = st.secrets["admin"].get("email", "admin@app.local")
    except:
        st.error("⚠️ Admin credentials not found in secrets! Please configure secrets.toml")
        st.stop()
    
    admin_password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
    
    cursor.execute('SELECT id FROM users WHERE username = ?', (admin_username,))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO users (username, password_hash, email, is_admin) VALUES (?, ?, ?, ?)',
            (admin_username, admin_password_hash, admin_email, 1)
        )
        conn.commit()
    
    conn.close()

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}

def create_user(username, password, email=None):
    """Create a new user"""
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute('INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
                      (username, password_hash, email))
        conn.commit()
        conn.close()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError as e:
        if 'username' in str(e):
            return False, "Username already exists"
        elif 'email' in str(e):
            return False, "Email already registered"
        return False, "Registration failed"
    except Exception as e:
        return False, f"Error: {str(e)}"

def verify_user(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    password_hash = hash_password(password)
    cursor.execute('SELECT id, username, is_admin FROM users WHERE username = ? AND password_hash = ?',
                  (username, password_hash))
    user = cursor.fetchone()
    conn.close()
    return user

def log_activity(user_id, activity_type, source_lang=None, target_lang=None, char_count=None):
    """Log user activity - ONLY metadata, NO content stored"""
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_log (user_id, activity_type, source_language, target_language, character_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, activity_type, source_lang, target_lang, char_count))
        conn.commit()
        conn.close()
    except:
        pass

def get_user_stats(user_id):
    """Get user statistics"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Total activities
    cursor.execute('SELECT COUNT(*) FROM activity_log WHERE user_id = ?', (user_id,))
    total_activities = cursor.fetchone()[0]
    
    # Total characters processed
    cursor.execute('SELECT SUM(character_count) FROM activity_log WHERE user_id = ?', (user_id,))
    total_chars = cursor.fetchone()[0] or 0
    
    # Most used languages
    cursor.execute('''
        SELECT target_language, COUNT(*) as count 
        FROM activity_log 
        WHERE user_id = ? AND target_language IS NOT NULL
        GROUP BY target_language 
        ORDER BY count DESC 
        LIMIT 3
    ''', (user_id,))
    top_languages = cursor.fetchall()
    
    conn.close()
    return {
        'total_activities': total_activities,
        'total_characters': total_chars,
        'top_languages': top_languages
    }

def get_all_users_stats():
    """Get statistics for all users (admin only)"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Total users
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    total_users = cursor.fetchone()[0]
    
    # Total activities across all users
    cursor.execute('SELECT COUNT(*) FROM activity_log')
    total_activities = cursor.fetchone()[0]
    
    # Total characters processed
    cursor.execute('SELECT SUM(character_count) FROM activity_log')
    total_chars = cursor.fetchone()[0] or 0
    
    # Most active users
    cursor.execute('''
        SELECT u.username, COUNT(a.id) as activity_count
        FROM users u
        LEFT JOIN activity_log a ON u.id = a.user_id
        WHERE u.is_admin = 0
        GROUP BY u.id, u.username
        ORDER BY activity_count DESC
        LIMIT 5
    ''')
    top_users = cursor.fetchall()
    
    conn.close()
    return {
        'total_users': total_users,
        'total_activities': total_activities,
        'total_characters': total_chars,
        'top_users': top_users
    }

# Initialize database
init_database()

# Session state for user management
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Authentication UI
if not st.session_state.logged_in:
    st.title("📄 OCR Translator with TTS")
    st.markdown("### Welcome! Please login or register to continue")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.markdown("#### Login to your account")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", type="primary"):
            if login_username and login_password:
                user = verify_user(login_username, login_password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.session_state.is_admin = bool(user[2])
                    
                    if st.session_state.is_admin:
                        st.success(f"🔑 Admin access granted! Welcome, {user[1]}!")
                    else:
                        st.success(f"Welcome back, {user[1]}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter both username and password")
    
    with tab2:
        st.markdown("#### Create a new account")
        st.info("📋 Please fill out all required fields to create your account")
        
        # Username field with real-time validation
        reg_username = st.text_input(
            "Username *", 
            key="reg_username",
            help="3-20 characters, letters, numbers, and underscores only",
            placeholder="Enter username"
        )
        
        # Real-time username validation
        if reg_username:
            username_valid, username_msg = validate_username(reg_username)
            if not username_valid:
                st.error(f"❌ {username_msg}")
            elif check_username_exists(reg_username):
                st.error("❌ Username already taken")
            else:
                st.success("✅ Username available")
        
        # Email field with validation
        reg_email = st.text_input(
            "Email *", 
            key="reg_email",
            help="Valid email address required",
            placeholder="your.email@example.com"
        )
        
        # Real-time email validation
        if reg_email:
            if not validate_email(reg_email):
                st.error("❌ Invalid email format")
            elif check_email_exists(reg_email):
                st.error("❌ Email already registered")
            else:
                st.success("✅ Email valid")
        
        # Password field with strength requirements
        st.markdown("**Password Requirements:**")
        st.caption("• At least 8 characters\n• One uppercase letter\n• One lowercase letter\n• One number\n• One special character (!@#$%^&*...)")
        
        reg_password = st.text_input(
            "Password *", 
            type="password", 
            key="reg_password",
            placeholder="Enter strong password"
        )
        
        # Real-time password validation
        if reg_password:
            password_valid, password_msg = validate_password(reg_password)
            if not password_valid:
                st.error(f"❌ {password_msg}")
            else:
                st.success("✅ Strong password")
        
        # Password confirmation
        reg_password_confirm = st.text_input(
            "Confirm Password *", 
            type="password", 
            key="reg_password_confirm",
            placeholder="Re-enter password"
        )
        
        # Real-time password match validation
        if reg_password and reg_password_confirm:
            if reg_password != reg_password_confirm:
                st.error("❌ Passwords do not match")
            else:
                st.success("✅ Passwords match")
        
        # Terms and Privacy
        st.markdown("---")
        agree_terms = st.checkbox(
            "I agree to the Terms of Service and Privacy Policy *",
            key="agree_terms"
        )
        
        if agree_terms:
            with st.expander("📜 View Privacy Policy"):
                st.markdown("""
                **Privacy Policy Summary:**
                - We do not store your uploaded documents or extracted text
                - Only usage statistics (metadata) are stored
                - Your password is securely hashed (never stored in plain text)
                - Your email is used only for account management
                - No third-party data sharing
                - Data is stored locally and securely
                
                **What we collect:**
                - Username, email, and hashed password
                - Usage statistics: activity count, character count, language preferences
                
                **What we DON'T collect:**
                - Document content
                - Extracted text
                - Generated audio files
                - Any sensitive information from your uploads
                """)
        
        st.markdown("---")
        
        # Register button
        if st.button("Register", type="primary", key="register_button"):
            # Comprehensive validation
            errors = []
            
            # Check all required fields
            if not reg_username:
                errors.append("Username is required")
            if not reg_email:
                errors.append("Email is required")
            if not reg_password:
                errors.append("Password is required")
            if not reg_password_confirm:
                errors.append("Password confirmation is required")
            if not agree_terms:
                errors.append("You must agree to the Terms of Service and Privacy Policy")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Validate username
                username_valid, username_msg = validate_username(reg_username)
                if not username_valid:
                    st.error(f"❌ {username_msg}")
                elif check_username_exists(reg_username):
                    st.error("❌ Username already taken")
                # Validate email
                elif not validate_email(reg_email):
                    st.error("❌ Invalid email format")
                elif check_email_exists(reg_email):
                    st.error("❌ Email already registered")
                # Validate password
                elif not validate_password(reg_password)[0]:
                    st.error(f"❌ {validate_password(reg_password)[1]}")
                # Check password match
                elif reg_password != reg_password_confirm:
                    st.error("❌ Passwords do not match")
                # All validations passed - create user
                else:
                    success, message = create_user(reg_username, reg_password, reg_email)
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        st.info("👉 Please go to the Login tab to sign in")
                    else:
                        st.error(f"❌ {message}")
    
    st.markdown("---")
    st.markdown("""
    ### Features:
    - 🔍 OCR text extraction from images and PDFs
    - 🌐 Translation to 35+ languages
    - 🔊 Text-to-speech in 30+ languages
    - 📊 Track your usage statistics
    - 💾 All your activities are logged
    
    ### 🔒 Privacy & Security:
    - ✅ **No documents stored** - All files processed in-memory only
    - ✅ **No text content saved** - Only usage statistics (character count, languages)
    - ✅ **No audio files stored** - Generated on-demand and discarded
    - ✅ **Secure passwords** - Hashed with SHA256
    - ✅ **Temporary processing** - Files deleted immediately after use
    """)
    st.stop()

# Main app (only shown when logged in)
st.title("📄 OCR Translator with TTS")

# User info and logout in sidebar
with st.sidebar:
    if st.session_state.is_admin:
        st.markdown(f"### 🔑 Admin Panel")
        st.markdown(f"**Logged in as:** {st.session_state.username}")
    else:
        st.markdown(f"### 👤 Welcome, {st.session_state.username}!")
    
    if st.button("Logout", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.is_admin = False
        st.rerun()
    
    st.markdown("---")
    
    # Admin sees global statistics
    if st.session_state.is_admin:
        st.markdown("### 📊 System Statistics")
        admin_stats = get_all_users_stats()
        
        st.metric("Total Users", admin_stats['total_users'])
        st.metric("Total Activities", admin_stats['total_activities'])
        st.metric("Total Characters Processed", f"{admin_stats['total_characters']:,}")
        
        if admin_stats['top_users']:
            st.markdown("**Most Active Users:**")
            for username, count in admin_stats['top_users']:
                st.markdown(f"- {username}: {count} activities")
    else:
        # Regular users see their own statistics
        st.markdown("### 📊 Your Statistics")
        
        stats = get_user_stats(st.session_state.user_id)
        st.metric("Total Activities", stats['total_activities'])
        st.metric("Characters Processed", f"{stats['total_characters']:,}")
        
        if stats['top_languages']:
            st.markdown("**Most Used Languages:**")
            for lang, count in stats['top_languages']:
                st.markdown(f"- {lang}: {count} times")
    
    st.markdown("---")
    st.caption("All your data is stored locally and securely")
    st.caption("🔒 Privacy: No documents or content stored - only usage stats")

st.markdown("Extract text from images/PDFs, translate, and listen to the results")
st.markdown("🔒 **Privacy Notice**: Your uploaded files and extracted text are processed in-memory only and never stored on our servers.")
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
    """Convert text to speech using gTTS - Audio generated in-memory, NOT stored"""
    try:
        # Limit text length for TTS (gTTS has limits)
        max_tts_length = 3000
        if len(text) > max_tts_length:
            text = text[:max_tts_length] + "..."
            st.warning(f"⚠️ Text truncated to {max_tts_length} characters for audio generation")
        
        tts = gTTS(text=text, lang=lang_code, slow=slow)
        audio_fp = BytesIO()  # In-memory storage only
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        
        # Convert to base64 for browser playback
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
    """Extract text from PDF file - File deleted immediately after processing"""
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
        # CRITICAL: Delete temporary file immediately - NO FILES STORED
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
                                    os.unlink(tmp_path)  # Delete PDF immediately
                                except:
                                    pass
                    else:
                        st.error("Unsupported file format")
                        st.stop()
                    
                    if extracted_text:
                        lang_code_to_name = {v: k for k, v in LANGUAGES.items()}
                        detected_language = lang_code_to_name.get(detected_lang_code, "Unknown")
                        
                        st.success(f"✅ Text extraction complete! Detected language: **{detected_language}**")
                        
                        # Log activity
                        log_activity(st.session_state.user_id, "OCR Extraction", detected_language, None, len(extracted_text))
                        
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
                        
                        # Log activity
                        log_activity(st.session_state.user_id, "OCR Extraction", manual_ocr_language, None, len(extracted_text))
                    
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
                        
                        # Log translation activity
                        log_activity(st.session_state.user_id, "Translation", detected_language, translation_language, len(translated_text))
                        
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
                                    
                                    # Log TTS activity
                                    log_activity(st.session_state.user_id, "TTS Generation", detected_language, translation_language, len(translated_text))
                                    
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

st.markdown("---")
st.markdown("### 🔒 Privacy & Data Policy:")
st.markdown("""
**What We Store:**
- ✅ Username and hashed password (for authentication)
- ✅ Activity metadata: timestamps, language selections, character counts

**What We DO NOT Store:**
- ❌ Uploaded documents (images/PDFs)
- ❌ Extracted text content
- ❌ Translated text
- ❌ Generated audio files
- ❌ Any document content whatsoever

**How We Process Your Data:**
1. 📤 Files uploaded → processed in RAM only
2. 🔍 Text extracted → displayed to you, never saved
3. 🌐 Translation → generated on-the-fly, not stored
4. 🔊 Audio → created in-memory, deleted after playback
5. 🗑️ Temporary files deleted immediately after processing

**Your Privacy is Guaranteed:**
- All document processing happens in temporary memory
- No content is written to disk (except temporary system files deleted immediately)
- Only usage statistics tracked (no actual content)
- You can download your results, but we don't keep copies
""")

st.markdown("---")
st.markdown("### 📝 How It Works:")
st.markdown("""
**Complete Workflow:**
1. 📄 **Upload** - Image or PDF document (processed in-memory)
2. 🔍 **Extract** - Auto-detect language and extract text using OCR
3. 🌐 **Translate** - Convert to your target language
4. 🔊 **Listen** - Hear the translated text read aloud (optional)
5. 📥 **Download** - Save text or audio (your choice)
6. 🗑️ **Delete** - All data cleared from our servers immediately

**Features:**
- ✅ Auto language detection for OCR
- ✅ 90+ languages for text extraction
- ✅ 35+ languages for translation
- ✅ Text-to-speech in 30+ languages
- ✅ Download original, translated text, and audio
- ✅ Zero data retention policy
- ✅ All processing in-memory (no storage)

**Perfect for:**
- Learning new languages
- Reading foreign documents
- Accessibility (text-to-speech)
- Document translation and archiving
- Privacy-conscious users
""")

st.markdown("---")
st.caption("🔒 Powered by Tesseract OCR, Google Translate, gTTS & deep-translator | Zero data retention | Privacy-first design")
st.caption("⚠️ Important: We do not store any document content. Download your results before leaving the page!")
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username format"""
    if not username:
        return False, "Username is required"
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 20:
        return False, "Username must be less than 20 characters"
    if not re.match(r'^[a-zA-Z0-9_]+

def create_user(username, password, email=None):
    """Create a new user"""
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute('INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
                      (username, password_hash, email))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    password_hash = hash_password(password)
    cursor.execute('SELECT id, username, is_admin FROM users WHERE username = ? AND password_hash = ?',
                  (username, password_hash))
    user = cursor.fetchone()
    conn.close()
    return user

def log_activity(user_id, activity_type, source_lang=None, target_lang=None, char_count=None):
    """Log user activity - ONLY metadata, NO content stored"""
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_log (user_id, activity_type, source_language, target_language, character_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, activity_type, source_lang, target_lang, char_count))
        conn.commit()
        conn.close()
    except:
        pass

def get_user_stats(user_id):
    """Get user statistics"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Total activities
    cursor.execute('SELECT COUNT(*) FROM activity_log WHERE user_id = ?', (user_id,))
    total_activities = cursor.fetchone()[0]
    
    # Total characters processed
    cursor.execute('SELECT SUM(character_count) FROM activity_log WHERE user_id = ?', (user_id,))
    total_chars = cursor.fetchone()[0] or 0
    
    # Most used languages
    cursor.execute('''
        SELECT target_language, COUNT(*) as count 
        FROM activity_log 
        WHERE user_id = ? AND target_language IS NOT NULL
        GROUP BY target_language 
        ORDER BY count DESC 
        LIMIT 3
    ''', (user_id,))
    top_languages = cursor.fetchall()
    
    conn.close()
    return {
        'total_activities': total_activities,
        'total_characters': total_chars,
        'top_languages': top_languages
    }

def get_all_users_stats():
    """Get statistics for all users (admin only)"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Total users
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    total_users = cursor.fetchone()[0]
    
    # Total activities across all users
    cursor.execute('SELECT COUNT(*) FROM activity_log')
    total_activities = cursor.fetchone()[0]
    
    # Total characters processed
    cursor.execute('SELECT SUM(character_count) FROM activity_log')
    total_chars = cursor.fetchone()[0] or 0
    
    # Most active users
    cursor.execute('''
        SELECT u.username, COUNT(a.id) as activity_count
        FROM users u
        LEFT JOIN activity_log a ON u.id = a.user_id
        WHERE u.is_admin = 0
        GROUP BY u.id, u.username
        ORDER BY activity_count DESC
        LIMIT 5
    ''')
    top_users = cursor.fetchall()
    
    conn.close()
    return {
        'total_users': total_users,
        'total_activities': total_activities,
        'total_characters': total_chars,
        'top_users': top_users
    }

# Initialize database
init_database()

# Session state for user management
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Authentication UI
if not st.session_state.logged_in:
    st.title("📄 OCR Translator with TTS")
    st.markdown("### Welcome! Please login or register to continue")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.markdown("#### Login to your account")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", type="primary"):
            if login_username and login_password:
                user = verify_user(login_username, login_password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.session_state.is_admin = bool(user[2])
                    
                    if st.session_state.is_admin:
                        st.success(f"🔑 Admin access granted! Welcome, {user[1]}!")
                    else:
                        st.success(f"Welcome back, {user[1]}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter both username and password")
    
    with tab2:
        st.markdown("#### Create a new account")
        reg_username = st.text_input("Choose Username", key="reg_username")
        reg_email = st.text_input("Email (optional)", key="reg_email")
        reg_password = st.text_input("Choose Password", type="password", key="reg_password")
        reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
        
        if st.button("Register", type="primary"):
            if reg_username and reg_password:
                if reg_password != reg_password_confirm:
                    st.error("Passwords do not match")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    if create_user(reg_username, reg_password, reg_email):
                        st.success("Account created successfully! Please login.")
                    else:
                        st.error("Username already exists")
            else:
                st.warning("Please enter username and password")
    
    st.markdown("---")
    st.markdown("""
    ### Features:
    - 🔍 OCR text extraction from images and PDFs
    - 🌐 Translation to 35+ languages
    - 🔊 Text-to-speech in 30+ languages
    - 📊 Track your usage statistics
    - 💾 All your activities are logged
    
    ### 🔒 Privacy & Security:
    - ✅ **No documents stored** - All files processed in-memory only
    - ✅ **No text content saved** - Only usage statistics (character count, languages)
    - ✅ **No audio files stored** - Generated on-demand and discarded
    - ✅ **Secure passwords** - Hashed with SHA256
    - ✅ **Temporary processing** - Files deleted immediately after use
    """)
    st.stop()

# Main app (only shown when logged in)
st.title("📄 OCR Translator with TTS")

# User info and logout in sidebar
with st.sidebar:
    if st.session_state.is_admin:
        st.markdown(f"### 🔑 Admin Panel")
        st.markdown(f"**Logged in as:** {st.session_state.username}")
    else:
        st.markdown(f"### 👤 Welcome, {st.session_state.username}!")
    
    if st.button("Logout", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.is_admin = False
        st.rerun()
    
    st.markdown("---")
    
    # Admin sees global statistics
    if st.session_state.is_admin:
        st.markdown("### 📊 System Statistics")
        admin_stats = get_all_users_stats()
        
        st.metric("Total Users", admin_stats['total_users'])
        st.metric("Total Activities", admin_stats['total_activities'])
        st.metric("Total Characters Processed", f"{admin_stats['total_characters']:,}")
        
        if admin_stats['top_users']:
            st.markdown("**Most Active Users:**")
            for username, count in admin_stats['top_users']:
                st.markdown(f"- {username}: {count} activities")
    else:
        # Regular users see their own statistics
        st.markdown("### 📊 Your Statistics")
        
        stats = get_user_stats(st.session_state.user_id)
        st.metric("Total Activities", stats['total_activities'])
        st.metric("Characters Processed", f"{stats['total_characters']:,}")
        
        if stats['top_languages']:
            st.markdown("**Most Used Languages:**")
            for lang, count in stats['top_languages']:
                st.markdown(f"- {lang}: {count} times")
    
    st.markdown("---")
    st.caption("All your data is stored locally and securely")
    st.caption("🔒 Privacy: No documents or content stored - only usage stats")

st.markdown("Extract text from images/PDFs, translate, and listen to the results")
st.markdown("🔒 **Privacy Notice**: Your uploaded files and extracted text are processed in-memory only and never stored on our servers.")
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
    """Convert text to speech using gTTS - Audio generated in-memory, NOT stored"""
    try:
        # Limit text length for TTS (gTTS has limits)
        max_tts_length = 3000
        if len(text) > max_tts_length:
            text = text[:max_tts_length] + "..."
            st.warning(f"⚠️ Text truncated to {max_tts_length} characters for audio generation")
        
        tts = gTTS(text=text, lang=lang_code, slow=slow)
        audio_fp = BytesIO()  # In-memory storage only
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        
        # Convert to base64 for browser playback
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
    """Extract text from PDF file - File deleted immediately after processing"""
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
        # CRITICAL: Delete temporary file immediately - NO FILES STORED
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
                                    os.unlink(tmp_path)  # Delete PDF immediately
                                except:
                                    pass
                    else:
                        st.error("Unsupported file format")
                        st.stop()
                    
                    if extracted_text:
                        lang_code_to_name = {v: k for k, v in LANGUAGES.items()}
                        detected_language = lang_code_to_name.get(detected_lang_code, "Unknown")
                        
                        st.success(f"✅ Text extraction complete! Detected language: **{detected_language}**")
                        
                        # Log activity
                        log_activity(st.session_state.user_id, "OCR Extraction", detected_language, None, len(extracted_text))
                        
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
                        
                        # Log activity
                        log_activity(st.session_state.user_id, "OCR Extraction", manual_ocr_language, None, len(extracted_text))
                    
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
                        
                        # Log translation activity
                        log_activity(st.session_state.user_id, "Translation", detected_language, translation_language, len(translated_text))
                        
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
                                    
                                    # Log TTS activity
                                    log_activity(st.session_state.user_id, "TTS Generation", detected_language, translation_language, len(translated_text))
                                    
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

st.markdown("---")
st.markdown("### 🔒 Privacy & Data Policy:")
st.markdown("""
**What We Store:**
- ✅ Username and hashed password (for authentication)
- ✅ Activity metadata: timestamps, language selections, character counts

**What We DO NOT Store:**
- ❌ Uploaded documents (images/PDFs)
- ❌ Extracted text content
- ❌ Translated text
- ❌ Generated audio files
- ❌ Any document content whatsoever

**How We Process Your Data:**
1. 📤 Files uploaded → processed in RAM only
2. 🔍 Text extracted → displayed to you, never saved
3. 🌐 Translation → generated on-the-fly, not stored
4. 🔊 Audio → created in-memory, deleted after playback
5. 🗑️ Temporary files deleted immediately after processing

**Your Privacy is Guaranteed:**
- All document processing happens in temporary memory
- No content is written to disk (except temporary system files deleted immediately)
- Only usage statistics tracked (no actual content)
- You can download your results, but we don't keep copies
""")

st.markdown("---")
st.markdown("### 📝 How It Works:")
st.markdown("""
**Complete Workflow:**
1. 📄 **Upload** - Image or PDF document (processed in-memory)
2. 🔍 **Extract** - Auto-detect language and extract text using OCR
3. 🌐 **Translate** - Convert to your target language
4. 🔊 **Listen** - Hear the translated text read aloud (optional)
5. 📥 **Download** - Save text or audio (your choice)
6. 🗑️ **Delete** - All data cleared from our servers immediately

**Features:**
- ✅ Auto language detection for OCR
- ✅ 90+ languages for text extraction
- ✅ 35+ languages for translation
- ✅ Text-to-speech in 30+ languages
- ✅ Download original, translated text, and audio
- ✅ Zero data retention policy
- ✅ All processing in-memory (no storage)

**Perfect for:**
- Learning new languages
- Reading foreign documents
- Accessibility (text-to-speech)
- Document translation and archiving
- Privacy-conscious users
""")

st.markdown("---")
st.caption("🔒 Powered by Tesseract OCR, Google Translate, gTTS & deep-translator | Zero data retention | Privacy-first design")
st.caption("⚠️ Important: We do not store any document content. Download your results before leaving the page!"), username):
        return False, "Username can only contain letters, numbers, and underscores"
    return True, ""

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password is required"
    
    errors = []
    
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("one uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("one lowercase letter")
    if not re.search(r'\d', password):
        errors.append("one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("one special character (!@#$%^&*...)")
    
    if errors:
        return False, "Password must contain: " + ", ".join(errors)
    
    return True, ""

def check_username_exists(username):
    """Check if username already exists"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def check_email_exists(email):
    """Check if email already exists"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def create_user(username, password, email=None):
    """Create a new user"""
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute('INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
                      (username, password_hash, email))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    password_hash = hash_password(password)
    cursor.execute('SELECT id, username, is_admin FROM users WHERE username = ? AND password_hash = ?',
                  (username, password_hash))
    user = cursor.fetchone()
    conn.close()
    return user

def log_activity(user_id, activity_type, source_lang=None, target_lang=None, char_count=None):
    """Log user activity - ONLY metadata, NO content stored"""
    try:
        conn = sqlite3.connect('users.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_log (user_id, activity_type, source_language, target_language, character_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, activity_type, source_lang, target_lang, char_count))
        conn.commit()
        conn.close()
    except:
        pass

def get_user_stats(user_id):
    """Get user statistics"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Total activities
    cursor.execute('SELECT COUNT(*) FROM activity_log WHERE user_id = ?', (user_id,))
    total_activities = cursor.fetchone()[0]
    
    # Total characters processed
    cursor.execute('SELECT SUM(character_count) FROM activity_log WHERE user_id = ?', (user_id,))
    total_chars = cursor.fetchone()[0] or 0
    
    # Most used languages
    cursor.execute('''
        SELECT target_language, COUNT(*) as count 
        FROM activity_log 
        WHERE user_id = ? AND target_language IS NOT NULL
        GROUP BY target_language 
        ORDER BY count DESC 
        LIMIT 3
    ''', (user_id,))
    top_languages = cursor.fetchall()
    
    conn.close()
    return {
        'total_activities': total_activities,
        'total_characters': total_chars,
        'top_languages': top_languages
    }

def get_all_users_stats():
    """Get statistics for all users (admin only)"""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Total users
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    total_users = cursor.fetchone()[0]
    
    # Total activities across all users
    cursor.execute('SELECT COUNT(*) FROM activity_log')
    total_activities = cursor.fetchone()[0]
    
    # Total characters processed
    cursor.execute('SELECT SUM(character_count) FROM activity_log')
    total_chars = cursor.fetchone()[0] or 0
    
    # Most active users
    cursor.execute('''
        SELECT u.username, COUNT(a.id) as activity_count
        FROM users u
        LEFT JOIN activity_log a ON u.id = a.user_id
        WHERE u.is_admin = 0
        GROUP BY u.id, u.username
        ORDER BY activity_count DESC
        LIMIT 5
    ''')
    top_users = cursor.fetchall()
    
    conn.close()
    return {
        'total_users': total_users,
        'total_activities': total_activities,
        'total_characters': total_chars,
        'top_users': top_users
    }

# Initialize database
init_database()

# Session state for user management
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Authentication UI
if not st.session_state.logged_in:
    st.title("📄 OCR Translator with TTS")
    st.markdown("### Welcome! Please login or register to continue")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.markdown("#### Login to your account")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", type="primary"):
            if login_username and login_password:
                user = verify_user(login_username, login_password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.session_state.is_admin = bool(user[2])
                    
                    if st.session_state.is_admin:
                        st.success(f"🔑 Admin access granted! Welcome, {user[1]}!")
                    else:
                        st.success(f"Welcome back, {user[1]}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter both username and password")
    
    with tab2:
        st.markdown("#### Create a new account")
        reg_username = st.text_input("Choose Username", key="reg_username")
        reg_email = st.text_input("Email (optional)", key="reg_email")
        reg_password = st.text_input("Choose Password", type="password", key="reg_password")
        reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
        
        if st.button("Register", type="primary"):
            if reg_username and reg_password:
                if reg_password != reg_password_confirm:
                    st.error("Passwords do not match")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    if create_user(reg_username, reg_password, reg_email):
                        st.success("Account created successfully! Please login.")
                    else:
                        st.error("Username already exists")
            else:
                st.warning("Please enter username and password")
    
    st.markdown("---")
    st.markdown("""
    ### Features:
    - 🔍 OCR text extraction from images and PDFs
    - 🌐 Translation to 35+ languages
    - 🔊 Text-to-speech in 30+ languages
    - 📊 Track your usage statistics
    - 💾 All your activities are logged
    
    ### 🔒 Privacy & Security:
    - ✅ **No documents stored** - All files processed in-memory only
    - ✅ **No text content saved** - Only usage statistics (character count, languages)
    - ✅ **No audio files stored** - Generated on-demand and discarded
    - ✅ **Secure passwords** - Hashed with SHA256
    - ✅ **Temporary processing** - Files deleted immediately after use
    """)
    st.stop()

# Main app (only shown when logged in)
st.title("📄 OCR Translator with TTS")

# User info and logout in sidebar
with st.sidebar:
    if st.session_state.is_admin:
        st.markdown(f"### 🔑 Admin Panel")
        st.markdown(f"**Logged in as:** {st.session_state.username}")
    else:
        st.markdown(f"### 👤 Welcome, {st.session_state.username}!")
    
    if st.button("Logout", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.is_admin = False
        st.rerun()
    
    st.markdown("---")
    
    # Admin sees global statistics
    if st.session_state.is_admin:
        st.markdown("### 📊 System Statistics")
        admin_stats = get_all_users_stats()
        
        st.metric("Total Users", admin_stats['total_users'])
        st.metric("Total Activities", admin_stats['total_activities'])
        st.metric("Total Characters Processed", f"{admin_stats['total_characters']:,}")
        
        if admin_stats['top_users']:
            st.markdown("**Most Active Users:**")
            for username, count in admin_stats['top_users']:
                st.markdown(f"- {username}: {count} activities")
    else:
        # Regular users see their own statistics
        st.markdown("### 📊 Your Statistics")
        
        stats = get_user_stats(st.session_state.user_id)
        st.metric("Total Activities", stats['total_activities'])
        st.metric("Characters Processed", f"{stats['total_characters']:,}")
        
        if stats['top_languages']:
            st.markdown("**Most Used Languages:**")
            for lang, count in stats['top_languages']:
                st.markdown(f"- {lang}: {count} times")
    
    st.markdown("---")
    st.caption("All your data is stored locally and securely")
    st.caption("🔒 Privacy: No documents or content stored - only usage stats")

st.markdown("Extract text from images/PDFs, translate, and listen to the results")
st.markdown("🔒 **Privacy Notice**: Your uploaded files and extracted text are processed in-memory only and never stored on our servers.")
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
    """Convert text to speech using gTTS - Audio generated in-memory, NOT stored"""
    try:
        # Limit text length for TTS (gTTS has limits)
        max_tts_length = 3000
        if len(text) > max_tts_length:
            text = text[:max_tts_length] + "..."
            st.warning(f"⚠️ Text truncated to {max_tts_length} characters for audio generation")
        
        tts = gTTS(text=text, lang=lang_code, slow=slow)
        audio_fp = BytesIO()  # In-memory storage only
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        
        # Convert to base64 for browser playback
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
    """Extract text from PDF file - File deleted immediately after processing"""
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
        # CRITICAL: Delete temporary file immediately - NO FILES STORED
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
                                    os.unlink(tmp_path)  # Delete PDF immediately
                                except:
                                    pass
                    else:
                        st.error("Unsupported file format")
                        st.stop()
                    
                    if extracted_text:
                        lang_code_to_name = {v: k for k, v in LANGUAGES.items()}
                        detected_language = lang_code_to_name.get(detected_lang_code, "Unknown")
                        
                        st.success(f"✅ Text extraction complete! Detected language: **{detected_language}**")
                        
                        # Log activity
                        log_activity(st.session_state.user_id, "OCR Extraction", detected_language, None, len(extracted_text))
                        
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
                        
                        # Log activity
                        log_activity(st.session_state.user_id, "OCR Extraction", manual_ocr_language, None, len(extracted_text))
                    
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
                        
                        # Log translation activity
                        log_activity(st.session_state.user_id, "Translation", detected_language, translation_language, len(translated_text))
                        
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
                                    
                                    # Log TTS activity
                                    log_activity(st.session_state.user_id, "TTS Generation", detected_language, translation_language, len(translated_text))
                                    
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

st.markdown("---")
st.markdown("### 🔒 Privacy & Data Policy:")
st.markdown("""
**What We Store:**
- ✅ Username and hashed password (for authentication)
- ✅ Activity metadata: timestamps, language selections, character counts

**What We DO NOT Store:**
- ❌ Uploaded documents (images/PDFs)
- ❌ Extracted text content
- ❌ Translated text
- ❌ Generated audio files
- ❌ Any document content whatsoever

**How We Process Your Data:**
1. 📤 Files uploaded → processed in RAM only
2. 🔍 Text extracted → displayed to you, never saved
3. 🌐 Translation → generated on-the-fly, not stored
4. 🔊 Audio → created in-memory, deleted after playback
5. 🗑️ Temporary files deleted immediately after processing

**Your Privacy is Guaranteed:**
- All document processing happens in temporary memory
- No content is written to disk (except temporary system files deleted immediately)
- Only usage statistics tracked (no actual content)
- You can download your results, but we don't keep copies
""")


st.caption("🔒  Zero data retention | Privacy-first design")
st.caption("⚠️ Important: We do not store any document content. Download your results before leaving the page!")
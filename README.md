# AudioBook Reader - OCR & TTS

A privacy-first Streamlit application that extracts text from images and PDFs, translates it into 34 languages, and converts it to speech in 30 languages. Built with a book/library-inspired UI for an immersive reading experience.

## Features

- **OCR Text Extraction** -- Process images (JPG, PNG) and PDFs with Tesseract OCR supporting 90 languages, including automatic language detection
- **Translation** -- Translate extracted text into 34 languages via Google Translate
- **Text-to-Speech** -- Generate audio in 30 languages with gTTS, featuring slow speech mode for language learning and auto-play
- **User Authentication** -- Secure registration and login with password strength validation and sha512_crypt hashing
- **Admin Dashboard** -- Librarian panel with global usage statistics, most active readers, and activity tracking
- **Privacy-First Design** -- No documents, text, or audio are stored on disk. All processing happens in temporary memory and is deleted immediately after use
- **Download Options** -- Export extracted text, translated text, and generated audio as files

## Prerequisites

- **Python 3.8+**
- **Tesseract OCR** -- Required for text extraction
  - Windows: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH
  - macOS: `brew install tesseract`
  - Linux: `sudo apt install tesseract-ocr`
- **Poppler** -- Required for PDF processing
  - Windows: Download from [poppler releases](https://github.com/osber/poppler-windows/releases), extract, and add `bin/` to PATH
  - macOS: `brew install poppler`
  - Linux: `sudo apt install poppler-utils`

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/TTS_test.git
cd TTS_test

# Install Python dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.streamlit/secrets.toml` file for admin credentials:

```toml
[admin]
username = "your_admin_username"
password = "your_secure_password"
```

This file is already included in `.gitignore` and will not be committed.

## Running

```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`.

## Supported Languages

| Feature | Count | Examples |
|---------|-------|---------|
| OCR | 90 languages | English, Chinese, Arabic, Japanese, Hindi, Korean, and more |
| Translation | 34 languages | English, German, Spanish, French, Italian, Portuguese, and more |
| TTS | 30 languages | English, German, Spanish, French, Italian, Japanese, and more |

Auto-detect mode tries the 10 most common languages first, then falls back to English if no meaningful text is found.

## Privacy & Security

- Uploaded documents are deleted immediately after processing
- Extracted and translated text is never written to disk
- Generated audio is created in memory and never saved
- Activity logs store only metadata (timestamps, language selections, character counts) -- never content
- Passwords are hashed with passlib's sha512_crypt
- Account deletion cascades to all associated data

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | Streamlit |
| OCR Engine | Tesseract OCR (via pytesseract) |
| PDF Processing | pdf2image + Poppler |
| Translation | Google Translate (via deep-translator) |
| Text-to-Speech | gTTS (Google Text-to-Speech) |
| Language Detection | langdetect |
| Image Processing | Pillow |
| Password Hashing | passlib (sha512_crypt) |
| Database | SQLite |

## License

Apache License 2.0 -- see [LICENSE](LICENSE) for details.

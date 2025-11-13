import streamlit as st
import speech_recognition as sr
import tempfile
import os

st.set_page_config(page_title="STT Test App", layout="centered")

st.title("🎤 Speech-to-Text Test App")
st.markdown("Test speech recognition functionality with no data storage")
st.markdown("---")

# Language selection
language = st.selectbox(
    "Select Language:",
    options=[
        ("English (US)", "en-US"),
        ("English (UK)", "en-GB"),
        ("German", "de-DE"),
        ("Spanish", "es-ES"),
        ("French", "fr-FR"),
        ("Italian", "it-IT"),
        ("Japanese", "ja-JP"),
        ("Chinese (Mandarin)", "zh-CN"),
    ],
    format_func=lambda x: x[0]
)

lang_code = language[1]

st.markdown("### Upload Audio File")
st.info("📝 Supported formats: WAV, MP3, FLAC, M4A, OGG")

# File uploader
audio_file = st.file_uploader(
    "Choose an audio file:", 
    type=['wav', 'mp3', 'flac', 'm4a', 'ogg'],
    label_visibility="collapsed"
)

if audio_file is not None:
    # Display uploaded file info
    st.success(f"✅ File uploaded: **{audio_file.name}** ({audio_file.size / 1024:.2f} KB)")
    
    # Display audio player
    st.audio(audio_file, format=f'audio/{audio_file.name.split(".")[-1]}')
    
    # Reset file pointer
    audio_file.seek(0)
    
    # Transcribe button
    if st.button("🎤 Transcribe Audio", type="primary"):
        with st.spinner("Processing audio... This may take a moment."):
            try:
                # Create a temporary file (deleted automatically after use)
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{audio_file.name.split(".")[-1]}') as tmp_file:
                    # Write uploaded file to temp location
                    tmp_file.write(audio_file.read())
                    tmp_path = tmp_file.name
                
                # Initialize recognizer
                recognizer = sr.Recognizer()
                
                # Convert audio file to recognizable format
                with sr.AudioFile(tmp_path) as source:
                    # Adjust for ambient noise
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    # Record audio data
                    audio_data = recognizer.record(source)
                
                # Perform speech recognition using Google's free service
                text = recognizer.recognize_google(
                    audio_data, 
                    language=lang_code,
                    show_all=False
                )
                
                # Display results
                st.success("✅ Transcription complete!")
                st.markdown("### 📄 Transcribed Text:")
                st.text_area(
                    "Result:", 
                    text, 
                    height=150,
                    label_visibility="collapsed"
                )
                
                # Word count
                word_count = len(text.split())
                st.caption(f"Word count: {word_count}")
                
            except sr.UnknownValueError:
                st.error("❌ Could not understand the audio. Please try:")
                st.markdown("""
                - A clearer recording
                - Less background noise
                - The correct language selection
                """)
                
            except sr.RequestError as e:
                st.error(f"❌ Error with the speech recognition service: {e}")
                st.info("💡 This usually means no internet connection or the service is temporarily unavailable.")
                
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                
            finally:
                # Clean up temporary file immediately
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except:
                    pass

else:
    st.info("👆 Please upload an audio file to begin transcription")

st.markdown("---")
st.markdown("### 📝 Tips for Best Results:")
st.markdown("""
- Use clear audio with minimal background noise
- WAV format typically works best
- Ensure the correct language is selected
- Keep audio files under 10 seconds for faster processing
""")

st.markdown("---")
st.caption("Powered by Google Speech Recognition (Free) | No data stored")
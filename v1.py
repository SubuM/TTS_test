import streamlit as st
import whisper
from gtts import gTTS
import tempfile
import os
from io import BytesIO
import base64

# Page configuration
st.set_page_config(
    page_title="Speech Converter - STT & TTS",
    page_icon="🎙️",
    layout="centered"
)

st.title("🎙️ Speech Converter")
st.markdown("Speech-to-Text & Text-to-Speech powered by OpenAI Whisper and gTTS")
st.markdown("---")

# Create tabs
tab1, tab2 = st.tabs(["🎤 Speech-to-Text (STT)", "🔊 Text-to-Speech (TTS)"])

# ============================================================
# TAB 1: SPEECH-TO-TEXT (STT)
# ============================================================
with tab1:
    st.header("Speech-to-Text with Whisper")
    st.markdown("Upload an audio file and transcribe it using OpenAI's Whisper")
    
    # Model selection
    model_size = st.selectbox(
        "Select Whisper Model:",
        options=[
            ("Tiny (~39 MB, Fastest)", "tiny"),
            ("Base (~74 MB, Fast)", "base"),
            ("Small (~244 MB, Balanced)", "small"),
            ("Medium (~769 MB, Accurate)", "medium"),
            ("Large (~1550 MB, Most Accurate)", "large"),
        ],
        format_func=lambda x: x[0],
        index=1,  # Default to 'base'
        key="stt_model"
    )
    
    model_name = model_size[1]
    
    # Language selection for STT
    language_stt = st.selectbox(
        "Select Language (optional - leave as Auto-detect for best results):",
        options=[
            ("Auto-detect", None),
            ("English", "en"),
            ("German", "de"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("Italian", "it"),
            ("Japanese", "ja"),
            ("Chinese", "zh"),
            ("Portuguese", "pt"),
            ("Russian", "ru"),
            ("Arabic", "ar"),
        ],
        format_func=lambda x: x[0],
        key="stt_language"
    )
    
    lang_code_stt = language_stt[1]
    
    # Additional options
    show_timestamps = st.checkbox("Show timestamps", value=False, key="stt_timestamps")
    
    st.markdown("### Upload Audio File")
    st.info("📝 Supported formats: MP3, WAV, M4A, FLAC, OGG, and more")
    
    # File uploader
    audio_file = st.file_uploader(
        "Choose an audio file:", 
        type=['mp3', 'wav', 'm4a', 'flac', 'ogg', 'opus', 'webm'],
        label_visibility="collapsed",
        key="stt_uploader"
    )
    
    if audio_file is not None:
        # Display uploaded file info
        st.success(f"✅ File uploaded: **{audio_file.name}** ({audio_file.size / 1024:.2f} KB)")
        
        # Display audio player
        st.audio(audio_file, format=f'audio/{audio_file.name.split(".")[-1]}')
        
        # Reset file pointer
        audio_file.seek(0)
        
        # Transcribe button
        if st.button("🎤 Transcribe with Whisper", type="primary", key="stt_button"):
            
            # Load model (cached after first run)
            with st.spinner(f"Loading Whisper model ({model_name})... This may take a moment on first run."):
                try:
                    model = whisper.load_model(model_name)
                except Exception as e:
                    st.error(f"❌ Error loading model: {e}")
                    st.stop()
            
            with st.spinner("Transcribing audio... Please wait."):
                tmp_path = None
                try:
                    # Create temporary file (will be deleted immediately after use)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{audio_file.name.split(".")[-1]}') as tmp_file:
                        tmp_file.write(audio_file.read())
                        tmp_path = tmp_file.name
                    
                    # Transcribe using Whisper
                    transcribe_options = {
                        "fp16": False,  # Use FP32 for CPU compatibility
                        "verbose": False
                    }
                    
                    if lang_code_stt:
                        transcribe_options["language"] = lang_code_stt
                    
                    result = model.transcribe(tmp_path, **transcribe_options)
                    
                    # Display results
                    st.success("✅ Transcription complete!")
                    
                    # Show detected language if auto-detect was used
                    if not lang_code_stt and "language" in result:
                        detected_lang = result["language"]
                        st.info(f"🌍 Detected language: **{detected_lang.upper()}**")
                    
                    st.markdown("### 📄 Transcribed Text:")
                    st.text_area(
                        "Result:", 
                        result["text"].strip(), 
                        height=200,
                        label_visibility="collapsed",
                        key="stt_result"
                    )
                    
                    # Word count
                    word_count = len(result["text"].split())
                    st.caption(f"Word count: {word_count}")
                    
                    # Show timestamps if requested
                    if show_timestamps and "segments" in result:
                        st.markdown("### ⏱️ Timestamps:")
                        for segment in result["segments"]:
                            start = segment['start']
                            end = segment['end']
                            text = segment['text'].strip()
                            
                            # Format timestamps as MM:SS
                            start_min, start_sec = divmod(int(start), 60)
                            end_min, end_sec = divmod(int(end), 60)
                            
                            st.markdown(f"`[{start_min:02d}:{start_sec:02d} → {end_min:02d}:{end_sec:02d}]` {text}")
                    
                except Exception as e:
                    st.error(f"❌ Transcription error: {e}")
                    st.info("💡 Try using a smaller model or check if the audio file is valid.")
                    
                finally:
                    # CRITICAL: Delete temporary file immediately
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
    
    else:
        st.info("👆 Please upload an audio file to begin transcription")
    
    st.markdown("---")
    st.markdown("### 📝 About Whisper Models:")
    st.markdown("""
    - **Tiny/Base**: Fast, good for simple transcription
    - **Small**: Best balance of speed and accuracy
    - **Medium/Large**: Most accurate, but slower
    
    **First run**: Model will be downloaded and cached (~39 MB to 1.5 GB depending on size)  
    **Subsequent runs**: Model loads instantly from cache
    """)

# ============================================================
# TAB 2: TEXT-TO-SPEECH (TTS)
# ============================================================
with tab2:
    st.header("Text-to-Speech with gTTS")
    st.markdown("Convert text to speech using Google Text-to-Speech")
    
    # Language selection for TTS
    language_tts = st.selectbox(
        "Select Language:",
        options=[
            ("English", "en"),
            ("German", "de"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("Italian", "it"),
            ("Japanese", "ja"),
            ("Chinese (Mandarin)", "zh-CN"),
            ("Portuguese", "pt"),
            ("Russian", "ru"),
            ("Arabic", "ar"),
            ("Hindi", "hi"),
            ("Korean", "ko"),
            ("Dutch", "nl"),
        ],
        format_func=lambda x: x[0],
        key="tts_language"
    )
    
    lang_code_tts = language_tts[1]
    
    # Text input
    text_input = st.text_area(
        "Enter text to convert to speech:",
        value="Hello! This is a text-to-speech test.",
        height=150,
        key="tts_input"
    )
    
    # Speed option
    slow_speech = st.checkbox("Slow speech (for language learning)", value=False, key="tts_slow")
    
    # Generate button
    if st.button("🔊 Generate & Play Audio", type="primary", key="tts_button"):
        if text_input.strip():
            with st.spinner("Generating audio..."):
                try:
                    # Generate with selected speed
                    tts = gTTS(text=text_input, lang=lang_code_tts, slow=slow_speech)
                    audio_fp = BytesIO()
                    tts.write_to_fp(audio_fp)
                    audio_fp.seek(0)
                    
                    # Convert to base64
                    audio_bytes = audio_fp.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()
                    
                    # Display audio player
                    audio_html = f"""
                    <audio controls autoplay style="width: 100%; margin-top: 10px;">
                        <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                        Your browser does not support the audio element.
                    </audio>
                    """
                    
                    st.success("✅ Audio generated successfully!")
                    st.markdown(audio_html, unsafe_allow_html=True)
                    
                    # Download button
                    audio_fp.seek(0)
                    st.download_button(
                        label="📥 Download Audio",
                        data=audio_fp,
                        file_name="speech.mp3",
                        mime="audio/mp3",
                        key="tts_download"
                    )
                    
                except Exception as e:
                    st.error(f"❌ Error generating audio: {e}")
        else:
            st.warning("Please enter some text first!")
    
    st.markdown("---")
    st.markdown("### 📝 About gTTS:")
    st.markdown("""
    - ✅ Natural-sounding speech
    - ✅ Supports 100+ languages
    - ✅ Browser-based audio playback
    - ✅ Optional slow speech mode for learning
    - ✅ Download audio as MP3
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>🎙️ Powered by OpenAI Whisper & gTTS | No data stored | All processing in-memory</p>
    </div>
    """,
    unsafe_allow_html=True
)
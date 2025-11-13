import streamlit as st
import whisper
import tempfile
import os

st.set_page_config(page_title="Whisper STT Test App", layout="centered")

st.title("🎤 Whisper Speech-to-Text Test App")
st.markdown("Powered by OpenAI's Whisper - High accuracy with no data storage")
st.markdown("---")

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
    index=1  # Default to 'base'
)

model_name = model_size[1]

# Language selection (Whisper supports 99 languages!)
language = st.selectbox(
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
    format_func=lambda x: x[0]
)

lang_code = language[1]

# Additional options
show_timestamps = st.checkbox("Show timestamps", value=False)

st.markdown("### Upload Audio File")
st.info("📝 Supported formats: MP3, WAV, M4A, FLAC, OGG, and more")

# File uploader
audio_file = st.file_uploader(
    "Choose an audio file:", 
    type=['mp3', 'wav', 'm4a', 'flac', 'ogg', 'opus', 'webm'],
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
    if st.button("🎤 Transcribe with Whisper", type="primary"):
        
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
                
                if lang_code:
                    transcribe_options["language"] = lang_code
                
                result = model.transcribe(tmp_path, **transcribe_options)
                
                # Display results
                st.success("✅ Transcription complete!")
                
                # Show detected language if auto-detect was used
                if not lang_code and "language" in result:
                    detected_lang = result["language"]
                    st.info(f"🌍 Detected language: **{detected_lang.upper()}**")
                
                st.markdown("### 📄 Transcribed Text:")
                st.text_area(
                    "Result:", 
                    result["text"].strip(), 
                    height=200,
                    label_visibility="collapsed"
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

st.markdown("---")
st.markdown("### ✨ Whisper Advantages:")
st.markdown("""
- ✅ Works offline after model download
- ✅ Supports 99 languages
- ✅ Very accurate (better than Google API for many languages)
- ✅ Can handle noisy audio
- ✅ Provides timestamps
- ✅ Auto-detects language
""")

st.markdown("---")
st.caption("Powered by OpenAI Whisper | No data stored | Model cached locally")
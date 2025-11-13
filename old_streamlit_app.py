import streamlit as st
from gtts import gTTS
from io import BytesIO
import base64

st.set_page_config(page_title="TTS Test App", layout="centered")

st.title("🔊 Text-to-Speech Test App")
st.markdown("Test gTTS (Google Text-to-Speech) functionality")
st.markdown("---")

def create_audio_player(text, lang='en'):
    """Create HTML5 audio player with base64 encoded audio"""
    try:
        # Generate TTS
        tts = gTTS(text=text, lang=lang, slow=False)
        audio_fp = BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        
        # Convert to base64
        audio_bytes = audio_fp.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
        # Create HTML5 audio player
        audio_html = f"""
        <audio controls autoplay style="width: 100%;">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            Your browser does not support the audio element.
        </audio>
        """
        
        return audio_html, None
    except Exception as e:
        return None, str(e)

# Language selection
language = st.selectbox(
    "Select Language:",
    options=[
        ("English", "en"),
        ("German", "de"),
        ("Spanish", "es"),
        ("French", "fr"),
        ("Italian", "it"),
        ("Japanese", "ja"),
        ("Chinese", "zh"),
    ],
    format_func=lambda x: x[0]
)

lang_code = language[1]

# Text input
text_input = st.text_area(
    "Enter text to convert to speech:",
    value="Hello! This is a text-to-speech test.",
    height=100
)

# Speed option
slow_speech = st.checkbox("Slow speech (for language learning)", value=False)

# Generate button
if st.button("🔊 Generate & Play Audio", type="primary"):
    if text_input.strip():
        with st.spinner("Generating audio..."):
            try:
                # Generate with selected speed
                tts = gTTS(text=text_input, lang=lang_code, slow=slow_speech)
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
                
            except Exception as e:
                st.error(f"❌ Error generating audio: {e}")
    else:
        st.warning("Please enter some text first!")

st.markdown("---")
st.caption("Powered by gTTS (Google Text-to-Speech)")
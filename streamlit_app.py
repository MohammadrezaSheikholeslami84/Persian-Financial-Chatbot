import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import io
import torch
import time
import whisper
from pydub import AudioSegment
# Let's assume these are your actual, non-mocked modules
from financial_core import process_request
from gmini import rag_response

# -----------------------------
# Cached function to load the Whisper model.
# Using st.cache_resource ensures the model is loaded only once.
# -----------------------------
@st.cache_resource
def load_whisper(device="cpu"):
    """Loads the Whisper model onto the specified device."""
    return whisper.load_model("large", device=device)

# -----------------------------
# Main Application Class
# -----------------------------
class App:
    def __init__(self):
        """Initializes the application, sets up the page configuration, and loads models."""
        st.set_page_config(
            page_title="چت‌بات هوشمند مالی",
            page_icon="🤖",
            layout="centered",
            initial_sidebar_state="expanded"
        )
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        with st.spinner("در حال بارگذاری مدل Whisper..."):
            self.whisper_model = load_whisper(self.device)

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "assistant", "content": "سلام! می‌توانید پیام متنی ارسال کنید یا با دکمه میکروفون، صدایتان را ضبط کنید."}
            ]

    def apply_custom_styles(self):
        """Applies custom CSS inspired by the provided HTML for a light, modern theme."""
        st.markdown("""
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap');
                
                :root {
                    --background-color: #f8f9fa;
                    --container-bg: #ffffff;
                    --header-bg: #0d2137;
                    --bot-bubble-bg: #eef1f5;
                    --user-bubble-bg: linear-gradient(135deg, #007bff, #0056b3);
                    --text-color-dark: #2c3e50;
                    --text-color-light: #ffffff;
                    --border-color: #e0e4e8;
                    --font-family: "Vazirmatn", sans-serif;
                }

                html, body, [class*="st-"], .stApp {
                    font-family: var(--font-family);
                    background-color: var(--background-color) !important; 
                }

                /* --- Main Chat Container --- */
                [data-testid="stAppViewContainer"] > .main > div:first-child {
                    background-color: var(--container-bg);
                    border-radius: 24px;
                    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.12);
                    padding: 0;
                    margin: 1rem;
                }
                
                /* --- Custom Header --- */
                div[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child {
                    background-color: var(--header-bg);
                    padding: 1.5rem;
                    border-top-left-radius: 24px;
                    border-top-right-radius: 24px;
                }
                
                div[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child h1 {
                    color: var(--text-color-light);
                    font-size: 1.6rem;
                    width: 100%;
                    text-align: center;
                }

                /* --- Chat Input --- */
                div[data-testid="stChatInput"] {
                    background-color: var(--container-bg);
                    border-bottom-left-radius: 24px;
                    border-bottom-right-radius: 24px;
                    border-top: 1px solid var(--border-color);
                }
                div[data-testid="stChatInput"] textarea {
                    background-color: #f0f2f5 !important;
                    color: var(--text-color-dark) !important;
                    border: none;
                    border-radius: 25px;
                    direction: rtl !important;
                }
                div[data-testid="stChatInput"] textarea:focus {
                    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.2) !important;
                }
                div[data-testid="stChatInput"] textarea::placeholder {
                    text-align: right !important;
                }

                /* --- Chat Messages --- */
                [data-testid="stChatMessage"] {
                    background-color: transparent !important;
                    border: none !important;
                    box-shadow: none !important;
                }

                [data-testid="stChatMessage"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stMarkdownContainer"] {
                    padding: 12px 20px;
                    border-radius: 18px;
                    line-height: 1.7;
                    font-size: 1.1rem;
                    width: 100%;
                }
                
                /* Bot Bubble */
                div[data-testid="stChatMessage"]:has(div[data-user-scroll-id="assistant"]) div[data-testid="stMarkdownContainer"] {
                    background-color: var(--bot-bubble-bg) !important;
                    color: var(--text-color-dark) !important;
                    border-bottom-left-radius: 6px;
                }

                /* User Bubble */
                 div[data-testid="stChatMessage"]:has(div[data-user-scroll-id="user"]) div[data-testid="stMarkdownContainer"] {
                    background: var(--user-bubble-bg) !important;
                    color: var(--text-color-light) !important;
                    border-bottom-right-radius: 6px;
                }
                
                /* RTL and Color Fix for all message content */
                div[data-testid="stMarkdownContainer"] p,
                div[data-testid="stMarkdownContainer"] ul,
                div[data-testid="stMarkdownContainer"] ol,
                div[data-testid="stMarkdownContainer"] li,
                div[data-testid="stMarkdownContainer"] strong,
                div[data-testid="stMarkdownContainer"] em {
                    color: inherit !important;
                    direction: rtl !important;
                    text-align: right !important;
                }

                /* --- Suggestion Chips --- */
                .stButton > button {
                    background-color: rgba(0, 0, 0, 0.05);
                    border: 1px solid var(--border-color);
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 0.9rem;
                    color: var(--text-color-dark);
                    transition: background-color 0.2s;
                    font-weight: 500;
                }
                .stButton > button:hover {
                    background-color: rgba(0, 0, 0, 0.1);
                    border-color: #007bff;
                }

            </style>
        """, unsafe_allow_html=True)

    def response_generator(self, user_input: str):
        """Simulates a streaming response from the backend."""
        bot_response_data = process_request(user_input)
        full_response = rag_response(user_input, bot_response_data.get("text", ""))
        for word in full_response.split():
            yield word + " "
            time.sleep(0.05)

    def handle_voice_input(self):
        """Manages the voice input functionality in the sidebar."""
        st.sidebar.header("🎙️ ورودی صوتی")
        st.sidebar.info("برای صحبت کردن روی 'START' کلیک کنید و پس از اتمام، 'STOP' را بزنید.")
        # ... (voice handling logic remains the same)
        webrtc_ctx = webrtc_streamer(
            key="microphone",
            mode=WebRtcMode.SENDONLY,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"audio": True, "video": False},
        )
        if not webrtc_ctx.state.playing: return
        st.sidebar.info("در حال گوش دادن...")
        if 'audio_buffer' not in st.session_state: st.session_state.audio_buffer = io.BytesIO()
        if webrtc_ctx.audio_receiver:
            try:
                audio_frames = webrtc_ctx.audio_receiver.get_frames(timeout=1)
                for frame in audio_frames:
                    sound = AudioSegment(data=frame.to_ndarray().tobytes(), sample_width=frame.format.bytes, frame_rate=frame.sample_rate, channels=len(frame.layout.channels))
                    st.session_state.audio_buffer.write(sound.raw_data)
            except Exception as e: st.sidebar.error(f"خطا در دریافت صدا: {e}")
        if st.sidebar.button("پردازش صدا"):
            if st.session_state.audio_buffer.tell() > 0:
                with st.spinner("در حال تبدیل صدا به متن..."):
                    st.session_state.audio_buffer.seek(0)
                    audio_segment = AudioSegment.from_raw(st.session_state.audio_buffer, sample_width=2, frame_rate=48000, channels=1)
                    wav_buffer = io.BytesIO()
                    audio_segment.export(wav_buffer, format="wav")
                    wav_buffer.seek(0)
                    result = self.whisper_model.transcribe(wav_buffer, language="fa", fp16=torch.cuda.is_available())
                    transcribed_text = result["text"]
                st.session_state.audio_buffer = io.BytesIO()
                if transcribed_text:
                    st.sidebar.success("صدا با موفقیت پردازش شد.")
                    st.session_state.user_input_to_process = transcribed_text
                    st.rerun()
                else: st.sidebar.warning("متنی تشخیص داده نشد. لطفا دوباره تلاش کنید.")

    def run(self):
        """The main function to run the Streamlit application UI."""
        self.apply_custom_styles()
        
        st.title("چت‌بات هوشمند مالی")
        
        self.handle_voice_input()

        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Display suggestion chips only at the start
        if len(st.session_state.chat_history) == 1:
            cols = st.columns(3)
            suggestions = ["قیمت دلار امروز؟", "نمودار شاخص کل", "آخرین اخبار اپل"]
            for i, suggestion in enumerate(suggestions):
                if cols[i].button(suggestion, use_container_width=True):
                    st.session_state.user_input_to_process = suggestion
                    st.rerun()

        user_input = None
        if prompt := st.chat_input("پیام خود را بنویسید..."):
            user_input = prompt
        elif "user_input_to_process" in st.session_state:
            user_input = st.session_state.pop("user_input_to_process")

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.chat_message("user").markdown(user_input)
            
            with st.chat_message("assistant"):
                full_response = st.write_stream(self.response_generator(user_input))

            st.session_state.chat_history.append({"role": "assistant", "content": full_response.strip()})
            st.rerun()

# -----------------------------
# Run the application
# -----------------------------
if __name__ == "__main__":
    app = App()
    app.run()


import streamlit as st
import time
# Let's assume these are your actual, non-mocked modules
from financial_core import process_request
from gmini import rag_response

# -----------------------------
# Main Application Class
# -----------------------------
class App:
    def __init__(self):
        """Initializes the application and sets up the page configuration."""
        st.set_page_config(
            page_title="چت‌بات هوشمند مالی",
            page_icon="🤖",
            layout="centered",
            initial_sidebar_state="collapsed"
        )
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "assistant", "content": "سلام! چطور می‌توانم در امور مالی به شما کمک کنم؟"}
            ]

    def apply_custom_styles(self):
        """Applies custom CSS for a Gemini-like dark theme."""
        st.markdown("""
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap');
                
                :root {
                    --background-color: #131314;      /* Gemini Dark Background */
                    --container-bg: #1e1f20;          /* Gemini UI Elements Background */
                    --header-bg: #1e1f20;              /* Header Background */
                    --bot-bubble-bg: #2a2a2e;           /* Bot message background */
                    --user-bubble-bg: #0b57d0;          /* User message background (Vibrant Blue) */
                    --text-color-dark: #e3e3e3;         /* Main light text color */
                    --text-color-light: #ffffff;       /* Brighter text color */
                    --border-color: #3c4043;           /* Borders */
                    --font-family: "Vazirmatn", sans-serif;
                }


                html, body, [class*="st-"], .stApp {
                    font-family: var(--font-family) !important;
                    background-color: var(--background-color) !important; 
                    color: var(--text-color-dark) !important;
                }

                /* --- Main Chat Container --- */
                [data-testid="stAppViewContainer"] > .main > div:first-child {
                    background-color: var(--container-bg) !important;
                    border-radius: 24px;
                    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.25); /* Adjusted shadow for dark theme */
                    padding: 0;
                    margin: 1rem;
                }
                
                /* --- Custom Header --- */
                div[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child {
                    background-color: var(--header-bg) !important;
                    padding: 1.5rem;
                    border-top-left-radius: 24px;
                    border-top-right-radius: 24px;
                }
                
                div[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child h1 {
                    color: var(--text-color-light) !important;
                    font-size: 1.6rem;
                    width: 100%;
                    text-align: center;
                }

                /* --- Chat Input --- */
                div[data-testid="stChatInput"] {
                    background-color: var(--container-bg) !important;
                    border-bottom-left-radius: 24px;
                    border-bottom-right-radius: 24px;
                    border-top: 1px solid var(--border-color);
                }
                div[data-testid="stChatInput"] textarea {
                    background-color: #2a2a2e !important; /* Dark input field */
                    color: var(--text-color-dark) !important;
                    border: none !important;
                    border-radius: 25px;
                    direction: rtl !important;
                }
                div[data-testid="stChatInput"] textarea:focus {
                    box-shadow: 0 0 0 3px rgba(138, 180, 248, 0.5) !important; /* Gemini-like focus ring */
                }
                div[data-testid="stChatInput"] textarea::placeholder {
                    text-align: right !important;
                    color: #9aa0a6; /* Lighter placeholder text */
                }

                /* --- Chat Messages --- */
                [data-testid="stChatMessage"] {
                    background-color: transparent !important;
                    border: none !important;
                    box-shadow: none !important;
                }

                /* General bubble styling using stable test-ids */
                [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
                    padding: 12px 20px !important;
                    border-radius: 18px !important;
                    line-height: 1.7 !important;
                    font-size: 1.1rem !important;
                    width: 100% !important;
                }

                /* Bot Bubble */
                div[data-testid="stChatMessage"]:has(div[data-user-scroll-id="assistant"]) [data-testid="stMarkdownContainer"] {
                    background-color: var(--bot-bubble-bg) !important;
                    color: var(--text-color-dark) !important;
                    border-bottom-left-radius: 6px !important;
                }

                /* User Bubble */
                div[data-testid="stChatMessage"]:has(div[data-user-scroll-id="user"]) [data-testid="stMarkdownContainer"] {
                    background: var(--user-bubble-bg) !important;
                    color: var(--text-color-light) !important;
                    border-bottom-right-radius: 6px !important;
                }
                
                /* RTL and Color Fix for all message content */
                [data-testid="stMarkdownContainer"] * {
                    color: inherit !important;
                    direction: rtl !important;
                    text-align: right !important;
                }

                /* --- Suggestion Chips --- */
                .stButton > button {
                    background-color: #2a2a2e !important; /* Dark chips */
                    border: 1px solid var(--border-color) !important;
                    border-radius: 16px !important;
                    padding: 6px 14px !important;
                    font-size: 0.9rem !important;
                    color: var(--text-color-dark) !important;
                    transition: background-color 0.2s;
                    font-weight: 500;
                }
                .stButton > button:hover {
                    background-color: #3c4043 !important; /* Darker hover */
                    border-color: #8ab4f8 !important; /* Gemini blue for hover border */
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

    def run(self):
        """The main function to run the Streamlit application UI."""
        self.apply_custom_styles()
        
        st.title("چت‌بات هوشمند مالی")
        
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
                    st.session_state.chip_input = suggestion
                    st.rerun()

        user_input = None
        if prompt := st.chat_input("پیام خود را بنویسید..."):
            user_input = prompt
        elif "chip_input" in st.session_state:
            user_input = st.session_state.pop("chip_input")

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


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
            page_icon="📝",
            layout="centered",
            initial_sidebar_state="auto",
            menu_items=None,
        )
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "assistant", "content": "سوال خود را در مورد قیمت انواع بازار های مالی بپرسید!"}
            ]

    def apply_rtl_styles(self):
        """Applies custom CSS to enforce right-to-left text alignment."""
        st.markdown("""
            <style>
                div[data-testid="stChatMessage"] {
                    direction: rtl;
                }
                div[data-testid="stChatInput"] textarea {
                    direction: rtl;
                }
                h1[data-testid="stHeading"] {
                    text-align: right;
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
            
    def clear_chat_history(self):
        """Clears the chat history and resets it to the initial message."""
        st.session_state.chat_history = [
            {"role": "assistant", "content": "سوال خود را در مورد قیمت انواع بازار های مالی بپرسید!"}
        ]

    def run(self):
        """The main function to run the Streamlit application UI."""
        
        self.apply_rtl_styles()

        with st.sidebar:
           # st.title("درباره")
           # st.info("این چت‌بات برای پاسخ به سوالات مالی شما با استفاده از مدل‌های زبان بزرگ طراحی شده است.")
            if st.button("پاک کردن گفتگو"):
                self.clear_chat_history()
                st.rerun()

        st.title("چت‌بات هوشمند مالی 💬")
        
        # Display prior chat messages
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Accept user input
        if prompt := st.chat_input("سوال خود را بنویسید"):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

        # Generate a new response if the last message is not from the assistant
        if st.session_state.chat_history[-1]["role"] != "assistant":
            with st.chat_message("assistant"):
                with st.spinner("در حال فکر کردن..."):
                    user_prompt = st.session_state.chat_history[-1]["content"]
                    full_response = st.write_stream(self.response_generator(user_prompt))
            
            message = {"role": "assistant", "content": full_response}
            st.session_state.chat_history.append(message)


# -----------------------------
# Run the application
# -----------------------------
if __name__ == "__main__":
    app = App()
    app.run()


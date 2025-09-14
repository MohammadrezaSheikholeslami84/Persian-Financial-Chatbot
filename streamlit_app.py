import streamlit as st
import time
from financial_core import process_request
from gmini import rag_response
import draw_chart  # handle_chart_request
import pandas as pd

class App:
    def __init__(self):
        st.set_page_config(
            page_title="چت‌بات هوشمند مالی",
            page_icon="💬",
            layout="centered"
        )
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "assistant", "type": "text", "content": "سوال خود را در مورد قیمت انواع بازار های مالی بپرسید!"}
            ]

    def apply_rtl_styles(self):
        st.markdown("""
        <style>
            /* اعمال فونت Inter روی کل اپ */
            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif;
            }

            /* راست‌چین کردن پیام‌ها و ورودی متن */
            div[data-testid="stChatMessage"] {
                direction: rtl;
                text-align: right;
            }
            div[data-testid="stChatInput"] textarea {
                direction: rtl;
                text-align: right;
            }
            h1[data-testid="stTitle"] {
                text-align: right;
                direction: rtl;
            }
        </style>
        """, unsafe_allow_html=True)

    def response_generator(self, user_input: str):
        bot_response_data = process_request(user_input)
        full_response = rag_response(user_input, bot_response_data.get("text", ""))
        for word in full_response.split():
            yield word + " "
            time.sleep(0.05)

    def clear_chat_history(self):
        st.session_state.chat_history = [
            {"role": "assistant", "type": "text", "content": "سوال خود را در مورد قیمت انواع بازار های مالی بپرسید!"}
        ]

    def run(self):
        self.apply_rtl_styles()

        with st.sidebar:
            if st.button("پاک کردن گفتگو"):
                self.clear_chat_history()
                st.rerun()

        st.title("چت‌بات هوشمند مالی 💬")

        # نمایش تاریخچه
        for message in st.session_state.chat_history:
            role = message["role"]
            msg_type = message.get("type", "text")

            if msg_type == "image":
                with st.chat_message(role):
                    st.image(message["image"], caption=message.get("caption", ""), use_container_width=True)
            else:
                with st.chat_message(role):
                    st.markdown(message["content"])

        # ورودی متنی
        if user_input := st.chat_input("سوال خود را بنویسید"):
            st.session_state.chat_history.append({"role": "user", "type": "text", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # پاسخ دستیار
            features = process_request(user_input)
            response_type = features.get("type")

            if response_type == "image":
                chart_buffer = features.get("image")
                caption = features.get("caption", "نمودار")
                response = {"role": "assistant", "type": "image", "image": chart_buffer, "caption": caption}
                with st.chat_message("assistant"):
                    st.image(response["image"], caption=response["caption"], use_container_width=True)
            else:
                with st.chat_message("assistant"):
                    with st.spinner("در حال فکر کردن..."):
                        full_response = st.write_stream(self.response_generator(user_input))
                response = {"role": "assistant", "type": "text", "content": full_response}

            st.session_state.chat_history.append(response)


if __name__ == "__main__":
    app = App()
    app.run()

import streamlit as st
import time
import sqlite3
from datetime import datetime
import yaml
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader
from financial_core import process_request
from gmini import rag_response
from io import BytesIO

# ------------------------------
# مدیریت پایگاه داده
# ------------------------------
DB_FILE = "chat_history_multiuser.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT,
            image_data BLOB,
            caption TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def get_session_keys(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sessions WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    keys = [row[0] for row in cursor.fetchall()]
    conn.close()
    return keys

def get_session_title(session_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM sessions WHERE id=?", (session_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "گفتگوی حذف شده"

def get_messages(session_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def add_session(session_id, user_id, title="گفتگوی جدید..."):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (id, user_id, title) VALUES (?, ?, ?)", (session_id, user_id, title))
    conn.commit()
    conn.close()

def update_session_title(session_id, new_title):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, session_id))
    conn.commit()
    conn.close()

def add_message(session_id, message):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    image_bytes = None
    if message.get("type") == "image" and isinstance(message.get("image"), BytesIO):
        image_bytes = message["image"].getvalue()
    cursor.execute(
        "INSERT INTO messages (session_id, role, type, content, image_data, caption) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, message['role'], message.get('type', 'text'), message.get('content'), image_bytes, message.get('caption'))
    )
    conn.commit()
    conn.close()

def delete_session_db(session_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
# ------------------------------

# ------------------------------
# اپلیکیشن اصلی
# ------------------------------
class App:
    def __init__(self):
        st.set_page_config(page_title="چت‌بات هوشمند مالی", page_icon="💬", layout="centered")
        init_db()
        self.apply_rtl_styles()

    def apply_rtl_styles(self):
        st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');
            * { font-family: 'Vazirmatn', Tahoma, sans-serif; }
            body { direction: rtl; }
            .stButton > button { width: 100%; }
            h1, h2, h3, h4, h5, h6 { text-align: center; }
        </style>
        """, unsafe_allow_html=True)

    def response_generator(self, user_input: str, bot_response_data: dict):
        full_response = rag_response(user_input, bot_response_data.get("text", ""))
        for word in full_response.split():
            yield word + " "
            time.sleep(0.05)

    def run_chatbot_interface(self, user_id, name, authenticator):
        if "session_keys" not in st.session_state or st.session_state.get("current_user") != user_id:
            st.session_state.current_user = user_id
            st.session_state.session_keys = get_session_keys(user_id)
            st.session_state.active_session = st.session_state.session_keys[0] if st.session_state.session_keys else None

        with st.sidebar:
            st.header(f"کاربر: {name}")
            authenticator.logout('خروج', 'main')

            if st.button("➕ گفتگوی جدید", use_container_width=True):
                new_session_id = f"جلسه-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
                add_session(new_session_id, user_id)
                st.session_state.session_keys.insert(0, new_session_id)
                st.session_state.active_session = new_session_id
                st.rerun()

            st.markdown("---")
            st.markdown("##### تاریخچه گفتگوها")
            for session_key in st.session_state.session_keys:
                title = get_session_title(session_key)
                if st.button(title, key=f"btn_{session_key}", use_container_width=True):
                    if st.session_state.active_session != session_key:
                        st.session_state.active_session = session_key
                        st.rerun()

            if st.session_state.session_keys:
                st.markdown("---")
                if st.button("🗑️ حذف گفتگوی فعلی", use_container_width=True):
                    active_key = st.session_state.active_session
                    delete_session_db(active_key)
                    st.session_state.session_keys.remove(active_key)
                    st.session_state.active_session = st.session_state.session_keys[0] if st.session_state.session_keys else None
                    st.rerun()

        st.title("چت‌بات هوشمند مالی 💬")

        if not st.session_state.active_session:
            st.info("یک گفتگوی جدید ایجاد کنید یا یکی از گفتگوهای قبلی را انتخاب نمایید.")
            return

        current_session_messages = get_messages(st.session_state.active_session)
        for message in current_session_messages:
            with st.chat_message(message["role"]):
                if message.get("type") == "image" and message.get("image_data"):
                    st.image(message["image_data"], caption=message.get("caption", ""), use_container_width=True)
                else:
                    st.markdown(message.get("content", ""))

        if user_input := st.chat_input("سوال خود را اینجا بنویسید..."):
            user_message = {"role": "user", "type": "text", "content": user_input}
            add_message(st.session_state.active_session, user_message)

            if len(current_session_messages) == 0:
                new_title = user_input[:35] + "..." if len(user_input) > 35 else user_input
                update_session_title(st.session_state.active_session, new_title)

            features = process_request(user_input)
            response_type = features.get("type")

            if response_type == "image":
                response = {"role": "assistant", "type": "image", "image": features.get("image"), "caption": features.get("caption")}
                add_message(st.session_state.active_session, response)
            else:
                # جمع کردن پاسخ متنی
                response_text = "".join(list(self.response_generator(user_input, features)))
                with st.chat_message("assistant"):
                    st.markdown(response_text)
                response = {"role": "assistant", "type": "text", "content": response_text}
                add_message(st.session_state.active_session, response)

            st.rerun()

    def run(self):
        with open('config.yaml') as file:
            config = yaml.load(file, Loader=SafeLoader)

        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days']
        )

        name = st.session_state.get("name")
        username = st.session_state.get("username")
        status = st.session_state.get("authentication_status")

        if status:
            self.run_chatbot_interface(username, name, authenticator)
        else:
            choice = st.radio("انتخاب کنید:", ("ورود", "ثبت نام"), horizontal=True, label_visibility="collapsed")
            if choice == "ورود":
                authenticator.login(location='main')
                if st.session_state.get("authentication_status"):
                    st.rerun()
                elif st.session_state.get("authentication_status") is False:
                    st.error("نام کاربری یا رمز عبور اشتباه است")
                elif st.session_state.get("authentication_status") is None:
                    st.warning("لطفا نام کاربری و رمز عبور خود را وارد کنید")
            elif choice == "ثبت نام":
                registered_user = authenticator.register_user(location="main", pre_authorized=None)
                if registered_user:
                    st.success("کاربر با موفقیت ثبت نام شد. اکنون از بخش ورود وارد شوید.")
                    with open('config.yaml', 'w', encoding='utf-8') as file:
                        yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
                    time.sleep(1)
                    st.rerun()


if __name__ == "__main__":
    app = App()
    app.run()

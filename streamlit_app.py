import streamlit as st
import time
import sqlite3
from datetime import datetime
import yaml
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader
from financial_core import process_request
import financial_core
from gmini import chat_financial_assistant
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

    def response_generator(self, user_input: str,history_text: str):
        full_response = chat_financial_assistant(user_input,history_text)
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
            with st.chat_message("user"):
                st.markdown(user_input)

            if len(current_session_messages) == 0:
                new_title = user_input[:35] + "..." if len(user_input) > 35 else user_input
                update_session_title(st.session_state.active_session, new_title)


            recent_messages = get_messages(st.session_state.active_session)[-5:]  # آخرین ۵ پیام
            history_text = ""
            for msg in recent_messages:
                role_prefix = "کاربر:" if msg["role"] == "user" else "دستیار:"
                content = msg.get("content", "")
                history_text += f"{role_prefix} {content}\n"

            features = process_request(user_input)
            response_type = features.get("type")

            if response_type == "image":
                response = {"role": "assistant", "type": "image", "image": features.get("image"), "caption": features.get("caption")}
                add_message(st.session_state.active_session, response)

            else:
                with st.chat_message("assistant"):
                    full_response = st.write_stream(self.response_generator(user_input,history_text))

                response = {"role": "assistant", "type": "text", "content": full_response}
                add_message(st.session_state.active_session, response)

            st.rerun()


    def run(self):
        with open('config.yaml', encoding='utf-8') as file:
            config = yaml.load(file, Loader=SafeLoader)

        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days']
        )

        # -------------------------
        # 📌 تب‌های اپلیکیشن
        # -------------------------
        menu = st.sidebar.radio("منو", ["چت‌بات", "درباره ما"])

        if menu == "چت‌بات":
            # اول وضعیت ورود بررسی میشه
            if "authentication_status" not in st.session_state:
                st.session_state["authentication_status"] = None
            if "welcome_shown" not in st.session_state:
                st.session_state["welcome_shown"] = False

            if st.session_state["authentication_status"]:
                # ✅ کاربر وارد شده → رابط چت‌بات
                name = st.session_state["name"]
                username = st.session_state["username"]

                # پیام خوش‌آمد از ربات (فقط یک بار)
                if not st.session_state["welcome_shown"]:
                    st.session_state["welcome_shown"] = True
                    st.info(f"🤖 سلام {name}! من ربات مالی شما هستم. آماده پاسخگویی به سوالات شما")

                self.run_chatbot_interface(username, name, authenticator)

            else:
                # ❌ کاربر وارد نشده → دکمه‌های ورود و ثبت‌نام
                choice = st.radio("انتخاب کنید:", ("ورود", "ثبت نام"), horizontal=True, label_visibility="collapsed")

                if choice == "ورود":
                    try:
                        authenticator.login(
                            captcha=True,
                            fields={'Form name':'ورود', 'Username':'نام کاربری', 'Password':'رمز عبور', 'Login':'ورود', 'Captcha':'کپچا'}
                        )
                    except Exception as e:
                        st.error(e)

                    if st.session_state.get("authentication_status"):
                        st.session_state["welcome_shown"] = False  # پیام خوش‌آمد بعد از لاگین
                        st.rerun()
                    elif st.session_state.get("authentication_status") is False:
                        st.error("نام کاربری یا رمز عبور اشتباه است")

                elif choice == "ثبت نام":
                    try:
                        email_of_registered_user,username_of_registered_user,name_of_registered_user = authenticator.register_user(
                            location='main',
                            password_hint=False,
                            clear_on_submit=True,
                            fields={'First name':'نام','Last name':'نام خانوادگی','Form name':'ثبت نام',
                                    'Email':'ایمیل','Username':'نام کاربری','Password':'رمز عبور',
                                    'Repeat password':'تکرار رمز عبور','Captcha':'کپچا','Register':'ثبت نام'}
                        )
                        if email_of_registered_user:
                            st.success("کاربر با موفقیت ثبت نام شد. اکنون به‌صورت خودکار وارد می‌شوید...")
                            with open('config.yaml', 'w', encoding='utf-8') as file:
                                yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
                            st.session_state['authentication_status'] = True
                            st.session_state['username'] = username_of_registered_user
                            st.session_state['name'] = name_of_registered_user
                            st.session_state["welcome_shown"] = False
                            st.rerun()
                        else:
                            st.warning("لطفا همه فیلدهای ثبت نام را پر کنید")

                    except Exception as e:
                        st.error(e)

        elif menu == "درباره ما":
            st.title("ℹ️ درباره چت‌بات هوشمند مالی")
            st.markdown("""
چت‌بات مالی فارسی، دستیار هوشمند مالی‌ای است که هدفش **تسهیل دسترسی به اطلاعات بازارهای مالی** در زمان واقعی و بررسی داده‌های تاریخی است.  
این پروژه تلاشی است برای ارائه خدمات کامل به کاربران فارسی‌زبان تا بتوانند بدون پیچیدگی، از قیمت‌ها، نمودارها و مقایسه‌های دقیق بهره ببرند.  

### 🛠️ قابلیت‌ها
- نمایش قیمت‌های زنده دارایی‌ها از جمله ارزها، سکه و طلا، رمزارزها، سهام ایران و سهام خارجی  
- امکان استعلام قیمت‌های گذشته و بررسی روند تاریخی تغییرات بازار  
- محاسبه میزان بازدهی دارایی‌ها در بازه‌های زمانی مختلف و مقایسه آن‌ها  
- تولید نمودارهای حرفه‌ای با برچسب‌های فارسی برای درک تصویری بهتر داده‌ها  
- پشتیبانی از رابط‌های مختلف:  
  -- رابط وب تعاملی  
  -- بات تلگرام برای دسترسی راحت‌تر و سریع‌تر از طریق پیام‌رسان  
- ذخیره‌سازی تاریخچه گفتگو برای هر کاربر  

### 🌍 بازارها و دارایی‌های تحت پوشش
- **ارزها**: دلار، یورو، پوند، درهم، دینار، فرانک، روبل  
- **طلا و سکه‌ها**: انس جهانی، سکه امامی، بهار آزادی و انواع سکه‌های دیگر  
- **رمزارزها**: بیت‌کوین، اتریوم, کاردانو, ریپل, تتر و دیگر رمزارزهای شناخته‌شده  
- **سهام ایران**: نمادهای بورسی مختلف همراه با شاخص‌ها مثل شاخص کل، شاخص هم‌وزن و فرابورس  
- **سهام خارجی**: اپل، گوگل، آمازون، تسلا و مایکروسافت  

🔒 سیستم دارای **ثبت‌نام و ورود امن** بوده و امکان مدیریت چند کاربر را فراهم می‌کند.  
""")



if __name__ == "__main__":
    app = App()
    app.run()

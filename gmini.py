import requests
import json
import os
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import re
import financial_core
import cohere
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(base_url='https://api.gapgpt.app/v1',api_key=api_key)


def rag_response(user_query, retriever_output, history_text=""):
    prompt = f"""
شما یک دستیار مالی حرفه‌ای و خوش‌برخورد هستید.

تاریخچه مکالمه قبلی:
{history_text}

کاربر پرسیده: "{user_query}"

داده‌های واکشی‌شده: {retriever_output}

دستورالعمل‌ها:
1. ابتدا پیام کاربر را با توجه به تاریخچه مکالمه بررسی کن.
   - اگر کاربر دوباره به موضوعی که قبلاً در تاریخچه مطرح شده اشاره کرد، پاسخ را بر اساس اطلاعات قبلی و داده‌های جدید ترکیب کن.
2. اگر پیام کاربر غلط املایی یا دستوری دارد، خودت آن را اصلاح کن و نسخه صحیح را به کاربر نشان بده.
   مثال: اگر کاربر نوشت "قیمت سهم وملی چن بود؟"، مدل باید اصلاح کند و نمایش دهد: "قیمت سهم وملی چند بود؟"
3. اگر پیام ناقص یا مبهم است و اطلاعات کافی برای پاسخ دادن ندارد، یک سؤال کوتاه برای روشن شدن موضوع از کاربر بپرس.
   مثال: "می‌توانید کمی توضیح بیشتری بدهید تا بهتر راهنمایی کنم؟"
4. اگر پیام واضح و کامل است، با استفاده از داده‌های واکشی‌شده و اطلاعات موجود در تاریخچه، پاسخ کوتاه، روان و محاوره‌ای بده.
5. هیچ مقدمه یا سلام اضافه نکن.
6. اگر داده‌ای موجود است، تاریخ و قیمت‌ها را تغییر نده.
7. متن پاسخ را تمیز و بدون تکرار ارائه کن.
8. اگر داده‌ای نیست، با دانش خودت پاسخ بده به شکلی طبیعی و دوستانه.

توجه: فقط در صورت نیاز (پیام ناقص یا مبهم) از کاربر سؤال بپرس، اما همیشه غلط‌های املایی و دستوری را خودت اصلاح و به کاربر نمایش بده.
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7
    )

    return response.choices[0].message.content

def chat_financial_assistant(user_input, history_text, model_correct="gpt-4o-mini", model_response="gpt-4o-mini"):
    """
    دستیار مالی یکپارچه:
    1. اصلاح متن کاربر (املایی + دستوری + فاصله/نیم‌فاصله)
    2. پردازش متن اصلاح‌شده (استخراج intent + واکشی داده‌ها)
    3. تولید پاسخ نهایی کوتاه و محاوره‌ای
    """

    # -----------------------------
    # مرحله 1: اصلاح متن کاربر
    # -----------------------------
    prompt_correct = f"""
        شما یک دستیار مالی هوشمند هستید. 

        ورودی شما: 
        - تاریخچه مکالمه: {history_text}
        - متن جدید کاربر: "{user_input}"

        وظیفه شما:
        1. غلط‌های املایی و دستوری متن کاربر را اصلاح کن.
        2. با توجه به تاریخچه، اگر متن کاربر مبهم است یا به موضوع قبلی اشاره دارد، آن را کامل و شفاف بازنویسی کن.
        4. معنی پیام کاربر را تغییر نده؛ فقط واضح و درستش کن.

        خروجی:
        فقط یک جمله‌ی اصلاح‌شده و شفاف از متن کاربر بده.
        """
    
    try:
        response = client.chat.completions.create(
            model=model_correct,
            messages=[{"role": "user", "content": prompt_correct}],
            temperature=0.1
        )
        corrected_text = response.choices[0].message.content.strip()
    except Exception as e:
        corrected_text = user_input  # fallback
        print("Error in correction:", e)

    #print("Corrected text:", corrected_text)

    # -----------------------------
    # مرحله 2: پردازش متن اصلاح‌شده
    # -----------------------------
    try:
        features = financial_core.extract_features(corrected_text)
        data = financial_core.process_request(corrected_text).get("text", "")
    except Exception as e:
        features, data = {}, ""
        print("Error in feature extraction or data fetch:", e)

    # -----------------------------
    # مرحله 3: تولید پاسخ نهایی
    # -----------------------------
    prompt_final = f"""
    شما یک دستیار مالی حرفه‌ای و خوش‌برخورد هستید.

    تاریخچه مکالمه: {history_text}
    پیام اصلاح‌شده کاربر: "{corrected_text}"
    داده‌های واکشی‌شده: {data}

    دستورالعمل‌ها:
    1. پاسخ کوتاه، روان و محاوره‌ای بده.
    2. هیچ مقدمه یا سلام اضافه نکن.
    3. داده‌ها را تغییر نده.
    4. اگر پیام کاربر ناقص یا مبهم است، مودبانه یک سؤال کوتاه بپرس.
    5. اگر داده‌ای نیست، با دانش خودت پاسخ بده به شکلی طبیعی و دوستانه.
    """
    try:
        response_final = client.chat.completions.create(
            model=model_response,
            messages=[{"role": "user", "content": prompt_final}],
            temperature=0.6
        )
        final_reply = response_final.choices[0].message.content.strip()
    except Exception as e:
        final_reply = "متاسفم، مشکلی در پردازش پیش آمد."
        print("Error in final response:", e)


    return final_reply


def correct_text_with_gpt_api(user_prompt: str, model: str = "gpt-4o") -> str:
    """
    اصلاح غلط‌های املایی و دستوری متن فارسی با استفاده از OpenAI Chat API.
    """

    correction_prompt = f"""
    شما یک دستیار متخصص هستید که متن‌های مالی فارسی را تصحیح می‌کند.
    وظیفه شما اصلاح اشتباهات املایی، دستوری و تایپی است و متن را قابل فهم کنید.
    تنها خروجی باید جمله تصحیح‌شده باشد، بدون هیچ توضیح اضافی.

    **Examples:**
    1. Original: "قیمت سهم وملی نسبت بسال پپش چه تغیر کرده ؟"
       Corrected: "قیمت سهم وملی نسبت به سال پیش چه تغییری کرده است؟"
    2. Original: "نمودار بیتکوین رو در شیش ماه کذشته بکش"
       Corrected: "نمودار بیت کوین را در شش ماه گذشته بکش"
    3. Original: "شاخص بورس امروز چن بود"
       Corrected: "شاخص بورس امروز چند بود؟"

    **Now correct this sentence:**
    "{user_prompt}"
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": correction_prompt}],
            temperature=0
        )
        corrected_text = response.choices[0].message.content.strip()
        return corrected_text
    except Exception:
        return user_prompt


def extract_features_with_gpt_api(user_prompt: str, model: str = "gpt-4o") -> dict:
    """
    استخراج ویژگی‌های کلیدی از درخواست مالی فارسی با استفاده از OpenAI Chat API.
    خروجی یک دیکشنری با keys: type, symbol, intent است.
    """

    extraction_prompt = f"""
    شما یک تحلیل‌گر دقیق درخواست‌های مالی هستید. متن فارسی زیر را تحلیل کنید و تنها یک آبجکت JSON بازگردانید با ساختار زیر:

    {{
      "type": یکی از ["currency", "gold", "iran_stock", "iran_index", "crypto", "america_stock", "unknown"],
      "symbol": نماد فارسی دارایی،
      "intent": یکی از ["get_price", "get_change", "get_chart"]
    }}

    **Keywords:**
    - Currency: ["دلار", "یورو", "پوند", "درهم", "دینار", "فرانک", "روبل"]
    - Gold: ["طلا", "سکه امامی", "سکه بهار آزادی", "ربع سکه", "نیم سکه", "سکه"]
    - Iran Stock: ["خودرو", "بکام", "شتران", ...]
    - Iran Index: ["شاخص کل", "شاخص بورس", "شاخص هم وزن","شاخص فرابورس"]
    - Crypto: ["بیت کوین", "اتریوم", "تتر"]

    **Examples:**
    - Input: "قیمت امروز دلار چنده؟"
      Output: {{"type": "currency", "symbol": "دلار", "intent": "get_price"}}
    - Input: "تغییرات سهام خودرو نسبت به سال گذشته چطور بوده؟"
      Output: {{"type": "iran_stock", "symbol": "خودرو", "intent": "get_change"}}
    - Input: "نمودار قیمت سهام بکام رو در ۳ ماه گذشته برام بکش"
      Output: {{"type": "iran_stock", "symbol": "بکام", "intent": "get_chart"}}
    - Input: "شاخص بورس امروز چند بود؟"
      Output: {{"type": "iran_index", "symbol": "شاخص بورس","intent": "get_price"}}

    **Text to analyze:**
    "{user_prompt}"
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0
        )

        result_str = response.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", result_str, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            raise ValueError("پاسخ دریافتی از GPT شامل یک آبجکت JSON معتبر نبود.")
    except json.JSONDecodeError as json_err:
        raise ValueError(f"خطا در پارس کردن JSON از GPT: {json_err}. پاسخ دریافتی: {result_str}")
    except Exception as e:
        raise ValueError(f"خطا در تحلیل درخواست با GPT: {e}")




def extract_features_with_gpt_fallback(user_prompt: str,regex_result, model="gpt-4o"):
    """
    ابتدا از تابع regex خود استفاده می‌کند.
    اگر خروجی ناقص یا خالی بود، GPT را صدا می‌زند و JSON دقیق باز می‌گرداند.
    """

    # بررسی کامل بودن خروجی regex
    valid = regex_result and "symbols" in regex_result and regex_result["symbols"]

    if valid:
        return regex_result

    # مرحله 2: اگر regex ناقص بود، از GPT کمک بگیر
    prompt = f"""
    شما یک تحلیل‌گر دقیق درخواست‌های مالی هستید. متن فارسی زیر را تحلیل کنید و تنها یک آبجکت JSON بازگردانید با ساختار:

    {{
      "symbols": [لیست نمادهای دارایی‌ها در متن],
      "type": یکی از ["currency", "gold", "iran_stock", "iran_index", "crypto", "america_stock", "unknown"],
      "date": تاریخ درخواست کاربر (اگر مشخص نیست "Unknown"),
      "time": زمان درخواست (اگر مشخص نیست "Unknown"),
      "Compare_Command": True/False،
      "Change_Command": True/False،
      "chart": True/False،
      "forecast": True/False
    }}

    متن کاربر: "{user_prompt}"
    """

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    result_str =  response.choices[0].message.content.strip()
    match = re.search(r"\{.*\}", result_str, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    else:
        raise ValueError(f"نتیجه GPT JSON معتبر نیست: {result_str}")
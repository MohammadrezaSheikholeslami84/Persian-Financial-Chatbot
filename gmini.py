import requests
import json
import os
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import re
import financial_core

import cohere
import os
co = cohere.ClientV2("fPl1LjBKiVzVUhmQpbCecyZHPuCBmiejt1BEbYW5")  # better: use environment variable for security

def rag_response(user_query, retriever_output):
    """
    user_query: متن سوال کاربر
    retriever_output: خروجی سیستم فعلی (مثلا قیمت یا مقایسه)
    """

    prompt = f"""
        شما یک دستیار هوشمند مالی بسیار حرفه‌ای و خوش‌برخورد هستی.
کاربر پرسیده: "{user_query}"

داده‌های واکشی‌شده:
{retriever_output}

پاسخ بده:
- کوتاه، روان و محاوره‌ای باش، سلام یا مقدمه اضافه لازم نیست.
- اگر داده‌ای هست، تاریخ و قیمت‌ها را تغییر نده و نگو اطلاعات کامل نیست.
- اگر داده‌ای نیست، با دانش خودت جواب بده طوری که مکالمه طبیعی شود.
"""

    response = co.chat(
        model="command-a-03-2025",  # Cohere chat model
        messages=[{"role": "user", "content": prompt}],
        max_tokens = 150,
        temperature = 0.6
    )

    # خروجی متن تولید شده توسط مدل
    return response.message.content[0].text


def call_gemini(prompt: str, api_key: str) -> str:

    """یک تابع عمومی برای ارسال درخواست به Gemini API."""

    model_name = "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.RequestException as e:
        raise ConnectionError(
            f"خطای شبکه: {e}. از اتصال اینترنت و فعال بودن VPN اطمینان حاصل کنید."
        )
    except (KeyError, IndexError) as e:
        raise ValueError(f"پاسخ نامعتبر از API دریافت شد: {response.text}")


def correct_text_with_gemini(user_prompt: str, api_key: str) -> str:
    """
    از Gemini برای اصلاح غلط‌های املایی و دستوری در متن ورودی استفاده می‌کند.
    """
    correction_prompt = f"""
    You are an expert assistant specializing in correcting Persian financial queries. Your task is to correct spelling, grammar, and typos in the user's input, making it clean and understandable. The output must be ONLY the corrected sentence.

    **Context:** The user is asking questions about the stock market, currencies, and gold in Iran. Pay close attention to financial terms and stock symbols.

    **Examples:**
    1. Original: "قیمت سهم وملی نسبت بسال پپش چه تغیر کرده ؟"
       Corrected: "قیمت سهم وملی نسبت به سال پیش چه تغییری کرده است؟"
    2. Original: "نمودار بیتکوین رو در شیش ماه کذشته بکش"
       Corrected: "نمودار بیت کوین را در شش ماه گذشته بکش"
    3. Original: "شاخص بورس امروز چن بود"
       Corrected: "شاخص بورس امروز چند بود؟"

    **Task:**
    Now, correct the following sentence.

    Original sentence: "{user_prompt}"

    Corrected sentence:
    """
    try:
        corrected_text = call_gemini(correction_prompt, api_key)
        return corrected_text.strip()
    except Exception as e:
        return user_prompt  


def extract_features_with_gemini(user_prompt: str, api_key: str) -> dict:
    """
    با استفاده از Gemini، ویژگی‌های کلیدی را از درخواست کاربر استخراج می‌کند.
    """
    # پرامپت بهبود یافته با استفاده از لیست کلمات کلیدی کاربر
    extraction_prompt = f"""
    You are a precise financial request analyzer. Your task is to analyze the following Persian text and return ONLY a single, clean JSON object with the specified structure. Do not add any explanations, notes, or text before or after the JSON object.

    The JSON object must have the following keys:
    - "type": Asset type. It MUST be one of these values: ["currency", "gold", "iran_stock", "iran_index", "crypto", "america_stock", "unknown"].
    - "symbol": The Persian symbol of the asset. Extract it from the text. It will likely be one of the keywords provided in the examples.
    - "intent": The user's intent. It MUST be one of these values: ["get_price", "get_change", "get_chart"].

    Here are lists of keywords to help you identify the correct type and symbol:
    - Currency Symbols: ["دلار", "یورو", "پوند", "درهم", "دینار", "فرانک", "روبل"]
    - Gold Symbols: ["طلا", "سکه امامی", "سکه بهار آزادی", "ربع سکه", "نیم سکه", "سکه"]
    - Iran Stock Symbols: ["خودرو", "بکام", "شتران", ...]
    - Iran Index Symbols: ["شاخص کل", "شاخص بورس", "شاخص هم وزن","شاخص فرابورس"]
    - Crypto Symbols: ["بیت کوین", "اتریوم", "تتر"]

    Examples:
    - Input: "قیمت امروز دلار چنده؟"
      Output: {{"type": "currency", "symbol": "دلار", "intent": "get_price"}}
    - Input: "تغییرات سهام خودرو نسبت به سال گذشته چطور بوده؟"
      Output: {{"type": "iran_stock", "symbol": "خودرو", "intent": "get_change"}}
    - Input: "نمودار قیمت سهام بکام رو در ۳ ماه گذشته برام بکش"
      Output: {{"type": "iran_stock", "symbol": "بکام", "intent": "get_chart"}}
    - Input: "شاخص بورس امروز چند بود؟"
      Output: {{"type": "iran_index", "symbol": "شاخص بورس","intent": "get_price"}}

    Now, analyze the following text:
    "{user_prompt}"
    """
    try:
        result_str = call_gemini(extraction_prompt, api_key)

        match = re.search(r"\{.*\}", result_str, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            raise ValueError("پاسخ دریافتی از Gemini شامل یک آبجکت JSON معتبر نبود.")

    except json.JSONDecodeError as json_err:
        raise ValueError(
            f"خطا در پارس کردن JSON از Gemini: {json_err}. پاسخ دریافتی: {result_str}"
        )
    except Exception as e:
        raise ValueError(f"خطا در تحلیل درخواست با Gemini: {e}")


# --- تابع جستجوی آنلاین با Gemini (ویرایش شده) ---
def find_data_with_gemini(user_prompt: str, api_key: str) -> str:
    """
    اگر داده در سیستم داخلی پیدا نشد، از Gemini برای جستجو در وب استفاده می‌کند.
    این تابع خود متن درخواست کاربر را دریافت می‌کند.
    """
    search_prompt = f"""
    You are an expert financial assistant with access to real-time web search.
    Find the answer to the following user's question from reliable web sources and provide a concise and accurate summary in Persian.

    User's question: "{user_prompt}"
    """
    print(
        f"[سیستم پشتیبان] در حال جستجو با Gemini برای سوال: '{user_prompt[:50]}...'..."
    )
    return call_gemini(search_prompt, api_key)


'''
def process_financial_request(features: dict) -> dict:
    """
    بر اساس ویژگی‌های استخراج شده، داده‌های مالی را از منابع مربوطه دریافت می‌کند.
    """
    data_type = features.get("type")
    symbol = features.get("symbol")
    time_period = features.get("time_period")
    intent = features.get("intent")

    if not all([data_type, symbol, time_period, intent]):
        raise ValueError("ویژگی‌های استخراج شده ناقص هستند.")

    if data_type in ["currency", "gold", "iran_stock", "iran_index", "crypto"]:
        # فراخوانی ماژول شبیه‌سازی شده
        #data = financial_data_provider.get_data(symbol, data_type, time_period)
        return {"data": data, "features": features}
    else:
        return {"data": "این نوع دارایی پشتیبانی نمی‌شود.", "features": features}
'''


def generate_final_response_with_gemini(original_prompt: str, processed_data: dict, api_key: str) -> str:
    """
    با استفاده از داده‌های دریافتی، یک پاسخ طبیعی و کامل تولید می‌کند.
    """
    
    generation_prompt = f"""
    شما یک دستیار هوشمند مالی بسیار حرفه‌ای و خوش‌برخورد هستی.
    درخواست اصلی کاربر این بوده: "{original_prompt}"

    اطلاعاتی که از سیستم مالی دریافت کرده‌ای این است:
    {json.dumps(processed_data, ensure_ascii=False, indent=2)}

    وظیفه شما:
    با استفاده از این اطلاعات، یک پاسخ کامل، روان و دوستانه به زبان فارسی به کاربر بده.
    - اگر داده‌ها یک رشته متنی هستند، آن را به شکلی زیبا در پاسخ خود بگنجان.
    - اگر داده‌ها یک آبجکت با جزئیات هستند، آن‌ها را به صورت یک گزارش خوانا ارائه بده.
    - اگر قصد کاربر "get_chart" بوده، به او بگو که نمودار در حال آماده‌سازی است (چون این اسکریپت فقط متن تولید می‌کند).
    - پاسخ شما باید مستقیم و مرتبط با سوال کاربر باشد.
    """
    return call_gemini(generation_prompt, api_key)

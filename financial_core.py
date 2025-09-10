from pyexpat import features
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
from urllib.parse import quote
import jalali_pandas
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import jdatetime
import streamlit as st
import os
import io
from matplotlib.ticker import FuncFormatter
import arabic_reshaper
from bidi.algorithm import get_display
import matplotlib.font_manager as fm
import comparison
import database_store
import currency
import gold
import cryptocurrency
import iran_index
import iran_symbol
import america_stock
import draw_chart
import gmini
import prediction 

keywords_path = os.path.join(
    os.path.dirname(__file__), "data", "Financial_keywords.json"
)
print("keywords_path: ", keywords_path)

with open(keywords_path, "r", encoding="utf-8") as f:
    keywords = json.load(f)
    currency_keywords = keywords["currency_keywords"]
    gold_keywords = keywords["gold_keywords"]
    stock_keywords = keywords["stock_keywords"]
    american_stock_symbols_keywords = keywords["american_stock_symbols_keywords"]
    index_symbols_keywords = keywords["index_symbols_keywords"]
    cryptocurrency_keywords = keywords["cryptocurrency_keywords"]
    iran_symbols_keywords = keywords["iran_symbols_keywords"]
    time_keywords = keywords["time_keywords"]
    PERSIAN_NUMBER_WORDS = keywords["PERSIAN_NUMBER_WORDS"]
    fixed_keywords = keywords["fixed_keywords"]
    forecast_keywords  = keywords["forecast_keywords"]


def parse_persian_time(query_text: str):

    today = date.today()

    if query_text == "هفتگی":
        return (today - timedelta(weeks=1)).strftime("%Y-%m-%d")

    elif query_text == "یکماهه" or query_text == "ماهانه":
        return (today - relativedelta(months=1)).strftime("%Y-%m-%d")

    elif query_text == "یکساله" or query_text == "سالانه":
        return (today - relativedelta(years=1)).strftime("%Y-%m-%d")

    persian_to_english_map = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    processed_text = query_text.translate(persian_to_english_map)

    def convert_persian_words_to_numbers(text):
        for word, num in PERSIAN_NUMBER_WORDS.items():
            text = re.sub(rf"\b{word}\b", str(num), text)
        return text

    processed_text = convert_persian_words_to_numbers(processed_text)
    pattern = re.compile(
        r"(\d+)\s+(روز|هفته|ماه|سال)\s*(ی)*\s*(?:گذشته|پیش|اخیر)")
    match = pattern.search(processed_text)

    if match:
        quantity = int(match.group(1))
        unit = match.group(2)

        end_date = today
        if unit == "روز":
            start_date = today - timedelta(days=quantity)
        elif unit == "هفته":
            start_date = today - timedelta(weeks=quantity)
        elif unit == "ماه":
            start_date = today - relativedelta(months=quantity)
        elif unit == "سال":
            start_date = today - relativedelta(years=quantity)

        return f"{start_date.strftime('%Y-%m-%d')}"

    # Sort keys by length (longest first) to avoid partial matches
    sorted_keywords = sorted(fixed_keywords.keys(), key=len, reverse=True)

    found_keyword = None
    for keyword in sorted_keywords:
        if keyword in query_text:
            found_keyword = fixed_keywords[keyword]
            break

    if found_keyword == "today":
        return today.strftime("%Y-%m-%d")

    if found_keyword == "yesterday":
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    if found_keyword == "last_week":
        start_date = today - timedelta(weeks=1)
        return f"{start_date.strftime('%Y-%m-%d')}"

    if found_keyword == "last_month":
        start_date = today - timedelta(days=30)
        return f"{start_date.strftime('%Y-%m-%d')}"

    if found_keyword == "last_year":
        start_date = today - timedelta(days=365)
        return f"{start_date.strftime('%Y-%m-%d')}"

    else:
        return today.strftime("%Y-%m-%d")


def clean_index_features(features):
    if "بورس" in features["symbols"] and any(k in features["symbols"] for k in ["شاخص کل", "شاخص بورس", "شاخص فرابورس", "شاخص هم وزن"]):
        features["symbols"].remove("بورس")
    if "سکه" in features["symbols"] and any(k in features["symbols"] for k in ["سکه امامی", "سکه بهار آزادی", "ربع سکه", "نیم سکه", "سکه بهار ازادی"]):
        features["symbols"].remove("سکه")
    return features


def extract_features(user_input):
    """Extract financial features from user input."""
    extracted_features = {"symbols": []}

    # --- Currency ---
    for word in sorted(currency_keywords, key=len, reverse=True):
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, user_input) and word not in extracted_features["symbols"]:
            extracted_features["type"] = "currency"
            extracted_features["symbols"].append(word)

    # --- Gold ---
    for word in sorted(gold_keywords, key=len, reverse=True):
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, user_input) and word not in extracted_features["symbols"]:
            extracted_features["type"] = "gold"
            extracted_features["symbols"].append(word)

    # --- Stocks ---
    for word in stock_keywords:
        if word in user_input:
            extracted_features["type"] = "stock"

            # American Stocks
            for words in american_stock_symbols_keywords:
                pattern = rf"\b{re.escape(words)}\b"
                if re.search(pattern, user_input) and words not in extracted_features["symbols"]:
                    extracted_features["sub_type"] = "America Stock"
                    extracted_features["symbols"].append(words)

            # Iranian Index
            for words in index_symbols_keywords:
                pattern = rf"\b{re.escape(words)}\b"

                if re.search(pattern, user_input) and words not in extracted_features["symbols"]:
                    print(words)
                    extracted_features["sub_type"] = "Iran Index"
                    extracted_features["symbols"].append(words)

            # Iranian Symbols (فولاد، بکام ...)
            for symbol in iran_symbols_keywords:
                pattern = rf"\b{re.escape(symbol)}\b"
                if re.search(pattern, user_input) and symbol not in extracted_features["symbols"] and "سهام" in user_input:
                    extracted_features["sub_type"] = "Iran Symbol"
                    extracted_features["symbols"].append(symbol)

    # --- Cryptocurrency ---
    for word in sorted(cryptocurrency_keywords, key=len, reverse=True):
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, user_input) and word not in extracted_features["symbols"]:
            extracted_features["type"] = "cryptocurrency"
            extracted_features["symbols"].append(word)

    # --- Date & Time ---
    extracted_features["date"] = parse_persian_time(user_input)
    for word, value in fixed_keywords.items():
        if word in user_input:
            extracted_features["time"] = value

    if extracted_features["date"] != parse_persian_time("امروز"):
        extracted_features["time"] = "Unknown"

    if extracted_features["date"] == parse_persian_time("امروز"):
        extracted_features["time"] = "today"

    if "time" not in extracted_features and extracted_features["date"] == parse_persian_time("امروز"):
        extracted_features["time"] = "today"
        extracted_features["date"] = parse_persian_time("امروز")  # Default Value

    extracted_features = clean_index_features(extracted_features)

    # --- Commands ---
    if ("مقایسه" in user_input or "بازدهی" in user_input) and len(extracted_features["symbols"]) >= 2:
        extracted_features["Compare_Command"] = True
    else:
        extracted_features["Compare_Command"] = False

    if "تغییر" in user_input or "نسبت به" in user_input or "بازده" in user_input or "عملکرد" in user_input:
        extracted_features["Change_Command"] = True
    else:
        extracted_features["Change_Command"] = False

    if "چارت" in user_input or "نمودار" in user_input:
        extracted_features["chart"] = True
    else:
        extracted_features["chart"] = False
        
    if any(word in user_input for word in forecast_keywords):
        extracted_features["forecast"] = True
    else:
        extracted_features["forecast"] = False
    

    return extracted_features


def url_converter(persian_term, market):
    final_url = ""
    base_url = "https://api.tgju.org/v1/stocks/instrument/history-data/"
    encoded_term = quote(persian_term)

    final_url = base_url + encoded_term
    final_url += "?order_dir=desc&market="
    final_url += market
    final_url += "&lang=fa"

    return final_url


def get_data_for_date(main_dataframe, date_str, currency_type, asset_name,unit = "تومان"):
    result_df = main_dataframe.copy()
    if result_df.empty:
        return "⚠️ هیچ داده‌ای برای نمایش وجود ندارد."

    gregorian_raw = result_df["تاریخ میلادی"]
    if isinstance(gregorian_raw, str):
        gregorian_dt = datetime.strptime(gregorian_raw, "%Y-%m-%d %H:%M:%S")
    else:
        gregorian_dt = gregorian_raw
    gregorian_date = gregorian_dt.strftime("%d/%m/%Y")  # روز/ماه/سال

    jalali_str = result_df["تاریخ شمسی"]  # رشته yyyy-mm-dd
    year, month, day = map(int, jalali_str.split("/"))
    jalali_dt = jdatetime.date(year, month, day)
    jalali_date = f"{jalali_dt.year}/{jalali_dt.month:02}/{jalali_dt.day:02}"

    if currency_type == "america_stock":
        price = f"{float(result_df['پایانی']):,.2f} دلار"
    elif currency_type == "iran-index":
        price = f"{float(result_df['پایانی']):,.0f} واحد"
    elif currency_type in ["cryptocurrency", "forex"]:
        price = f"{float(result_df['پایانی']):,.2f} دلار"
    elif unit == "دلار":
        price = f"{float(result_df['پایانی']):,.2f} دلار"
    else:
        price = f"{float(result_df['پایانی']):,.0f} تومان"

    return f"قیمت {asset_name} در تاریخ {jalali_date} (معادل {gregorian_date}) برابر با {price} بوده است."


def process_request(user_input):
    os.environ["GOOGLE_API_KEY"] = "AIzaSyCykh_9usou6lXPxrItJ4ajCB4BvWr6Nq0"

    api_key = os.environ.get("GOOGLE_API_KEY")
    print(api_key)  # باید کلیدت رو چاپ کنه

    features = extract_features(user_input)
    print(features)  # برای دیباگ

    full_history_df = None

    #print(gmini.call_gemini(user_input, api_key))
    
   # if api_key is not None:
        #print(gmini.extract_features_with_gemini(user_input, api_key))
  #  else:
       # print("API key for Gemini is missing.")

    if not features["chart"] and not features.get("Compare_Command", False) :
        # ==================== Currency ====================
        if features["type"] == "currency":
            
            if features["time"] == "today" and not features["forecast"]:
                text = currency.get_currency_price_tgju(
                    features["symbols"][0])[0]
                # print(gmini.generate_final_response_with_gemini(user_input,{"type": "text", "text": text},api_key))
                return {"type": "text", "text": text}

            else:

                table_name = f"currency_{features['symbols'][0]}"
                print(table_name)

                dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                if not dataframe.empty:
                    print(f"Fetching data for {features['symbols'][0]} from DB.")

                else:
                    print(f"Fetching data for {features['symbols'][0]} from API and Saving to DB")
                    full_history_df = currency.get_history_currency2(features["symbols"][0])
                    dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                if features["Change_Command"] and not features["chart"]:
                    text = currency.get_currency_change(dataframe, features["symbols"][0], features["date"])[0]
                    return {"type": "text", "text": text}

                # ==================== Prediction ====================    
                elif features["forecast"]:
                    df = database_store.get_data_from_db(table_name)
                    results = prediction.predict(df,user_input,number_years=4)
                    if not results:
                        return {"type": "text", "text": "❌ داده‌ای برای پیش بینی پیدا نشد."}

                    return {"type": "text", "text": results}

                else:
                    text = get_data_for_date(dataframe, str(features["date"]), "currency", features["symbols"][0])
                    return {"type": "text", "text": text}

        # ==================== Gold ====================
        elif features["type"] == "gold":

            if features["time"] == "today" and not features["forecast"]:
                text = gold.get_gold_price_tgju(features["symbols"][0])[0]
                return {"type": "text", "text": text}

            else:

                keywords_path2 = os.path.join(os.path.dirname(__file__), "data", "golds.json")

                with open(keywords_path2, "r", encoding="utf-8") as f:
                    indexs = json.load(f)
                    
                mapping = indexs["mapping"]
                input_name = mapping.get(features['symbols'][0], features['symbols'][0])
                table_name = f"gold_{input_name}"
                
                api_map = indexs["MARKET_URLS"]
                url = api_map.get(input_name)

                unit = ""
                if "coin"  in url or "chart" in url:  # سکه‌ها
                    unit = "تومان"
                else:  # انس‌ها (دلاری)
                    unit = "دلار"

                print(table_name)

                dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                if not dataframe.empty:
                    print(f"Fetching data for {features['symbols'][0]} from DB.")

                else:
                    print(f"Fetching data for {features['symbols'][0]} from API and Saving to DB")
                    full_history_df = gold.get_history_gold2(features["symbols"][0])
                    dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                if features["Change_Command"] and not features["chart"]:
                    text = gold.get_gold_change(dataframe, features["symbols"][0], features["date"])[0]
                    return {"type": "text", "text": text}
                
                # ==================== Prediction ====================    
                elif features["forecast"]:
                    results = prediction.predict(full_history_df)
                    if not results:
                        return {"type": "text", "text": "❌ داده‌ای برای پیش بینی پیدا نشد."}

                    return {"type": "text", "text": results}

                else:
                    text = get_data_for_date(dataframe, str(features["date"]), "gold", features["symbols"][0],unit)
                    return {"type": "text", "text": text}

        # ==================== Stock ====================
        elif features["type"] == "stock":

            # ==================== America Stock ====================
            if features["sub_type"] == "America Stock":
                if features["time"] == "today" and not features["forecast"]:
                    text = america_stock.get_america_stock_price(features["symbols"][0])[0]
                    return {"type": "text", "text": text}

                else:

                    table_name = f"america_stock_{features['symbols'][0]}"
                    # print(table_name)

                    dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                    if not dataframe.empty:
                        print(f"Fetching data for {features['symbols'][0]} from DB.")

                    else:
                        print(f"Fetching data for {features['symbols'][0]} from API and Saving to DB")
                        full_history_df = america_stock.get_history_america_stock2(features["symbols"][0])
                        dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                    if features["Change_Command"] and not features["chart"]:
                        text = america_stock.get_america_stock_change(dataframe, features["symbols"][0], features["date"])[0]
                        return {"type": "text", "text": text}
                    
                    # ==================== Prediction ====================    
                    elif features["forecast"]:
                        results = prediction.predict(full_history_df)
                        if not results:
                            return {"type": "text", "text": "❌ داده‌ای برای پیش بینی پیدا نشد."}

                        return {"type": "text", "text": results}


                    else:
                        text = get_data_for_date(
                            dataframe,
                            str(features["date"]),
                            "america_stock",
                            features["symbols"][0],
                        )
                        return {"type": "text", "text": text}

            # ==================== Iran Index ====================
            elif features["sub_type"] == "Iran Index":

                if features["time"] == "today" and not features["forecast"]:
                    text = iran_index.get_iran_index_data(features["symbols"][0])[0]
                    return {"type": "text", "text": text}

                else:

                    table_name = f"iran_index_{features['symbols'][0]}"
                    # print(table_name)

                    dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                    if not dataframe.empty:
                        print(f"Fetching data for {features['symbols'][0]} from DB.")

                    else:
                        print(f"Fetching data for {features['symbols'][0]} from API and Saving to DB")
                        full_history_df = iran_index.get_history_iran_index2(features["symbols"][0])
                        dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                    if features["Change_Command"] and not features["chart"]:
                        text = iran_index.get_iran_index_change(dataframe, features["symbols"][0], features["date"])[0]
                        return {"type": "text", "text": text}
                    
                    # ==================== Prediction ====================    
                    elif features["forecast"]:
                        results = prediction.predict(full_history_df)
                        if not results:
                            return {"type": "text", "text": "❌ داده‌ای برای پیش بینی پیدا نشد."}

                        return {"type": "text", "text": results}

                    else:
                        text = get_data_for_date(
                            dataframe,
                            str(features["date"]),
                            "iran-index",
                            features["symbols"][0],
                        )
                        return {"type": "text", "text": text}

            # ==================== Iran Symbol ====================
            else:
                if features["time"] == "today" and not features["forecast"]:
                    text = iran_symbol.get_iran_symbol_data(features["symbols"][0])[0]
                    return {"type": "text", "text": text}

                else:
                    table_name = f"iran_symbol_{features['symbols'][0]}"
                    # print(table_name)

                    dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                    if not dataframe.empty:
                        print(f"Fetching data for {features['symbols'][0]} from DB.")

                    else:
                        print(f"Fetching data for {features['symbols'][0]} from API and Saving to DB")
                        full_history_df = iran_symbol.get_history_iran_symbol2(features["symbols"][0])
                        dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                    if features["Change_Command"] and not features["chart"]:
                        text = iran_symbol.get_iran_symbol_change(dataframe, features["symbols"][0], features["date"])[0]
                        return {"type": "text", "text": text}
                    
                    # ==================== Prediction ====================    
                    elif features["forecast"]:
                        results = prediction.predict(full_history_df)
                        if not results:
                            return {"type": "text", "text": "❌ داده‌ای برای پیش بینی پیدا نشد."}

                        return {"type": "text", "text": results}

                    else:
                        text = get_data_for_date(
                            dataframe,
                            str(features["date"]),
                            "iran-stock",
                            features["symbols"][0],
                        )
                        return {"type": "text", "text": text}

        # ==================== Cryptocurrency ====================
        elif features["type"] == "cryptocurrency":
            if features["time"] == "today" and not features["forecast"]:
                text = cryptocurrency.get_cryptocurrency_price_tgju(
                    features["symbols"][0])[0]
                return {"type": "text", "text": text}

            else:
                table_name = f"cryptocurrency_{features['symbols'][0]}"
                # print(table_name)

                dataframe = database_store.get_closest_row_as_df(table_name, features["date"])
                
                if not dataframe.empty:
                    print(f"Fetching data for {features['symbols'][0]} from DB.")
                else:
                    print(f"Fetching data for {features['symbols'][0]} from API and Saving to DB")
                    full_history_df = cryptocurrency.get_history_cryptocurrency2(features["symbols"][0])
                    dataframe = database_store.get_closest_row_as_df(table_name, features["date"])

                if features["Change_Command"] and not features["chart"]:
                    text = cryptocurrency.get_cryptocurrency_change(dataframe, features["symbols"][0], features["date"])[0]
                    return {"type": "text", "text": text}
                
                
                # ==================== Prediction ====================    
                elif features["forecast"]:
                    results = prediction.predict(full_history_df)
                    if not results:
                        return {"type": "text", "text": "❌ داده‌ای برای پیش بینی پیدا نشد."}

                    return {"type": "text", "text": results}

                else:
                    text = get_data_for_date(
                        dataframe,
                        str(features["date"]),
                        "cryptocurrency",
                        features["symbols"][0],
                    )
                    return {"type": "text", "text": text}

    # ==================== Comparison ====================
    elif features.get("Compare_Command", False):
        results = comparison.compare_assets(
            features["symbols"], features["date"])
        if not results:
            return {"type": "text", "text": "❌ داده‌ای برای مقایسه پیدا نشد."}

        return {"type": "text", "text": results}

    # ==================== Chart Type ====================
    elif features["chart"]:
        chart_result = draw_chart.handle_chart_request(features)
        return {
            "type": "image",
            "image": chart_result,
            "caption": f"📈 نمودار قیمت {features['symbols'][0]} از تاریخ {features['date']}",
        }
         
    # ==================== Unknown Type ====================
    else:
        print("[DEBUG] process_request output type:", type(text))
        return {"type": "text", "text": "❌ نوع درخواست مشخص نیست یا پشتیبانی نمی‌شود."}

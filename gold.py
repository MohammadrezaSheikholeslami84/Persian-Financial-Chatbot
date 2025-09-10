import re
import jdatetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
import database_store
import json
import os

def get_gold_price_tgju(input_name):

    keywords_path = os.path.join(os.path.dirname(__file__), "data", "golds.json")
    print("keywords_path: ", keywords_path)

    with open(keywords_path, "r", encoding="utf-8") as f:
        indexs = json.load(f)
        
    MARKET_URLS = indexs["MARKET_URLS"]
    mapping = indexs["mapping"]
    

    input_name = mapping.get(input_name, input_name)
    url = MARKET_URLS.get(input_name)

    if not url:
        return f"{input_name} پشتیبانی نمی‌شود", None

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    html = response.text

    # پیدا کردن ردیف مربوط به ارز/سکه
    row_pattern = re.compile(
        rf'<tr.*?>\s*<th.*?>\s*{re.escape(input_name)}\s*</th>(.*?)</tr>',
        re.DOTALL
    )
    match_row = row_pattern.search(html)
    if not match_row:
        return f"{input_name} پیدا نشد", None

    row_html = match_row.group(1)

    # --- استخراج قیمت ---
    price_match = re.search(r'<td.*?>([\d,\.]+)</td>', row_html)
    price_raw = price_match.group(1) if price_match else "0"

    # --- استخراج درصد و مقدار تغییر ---
    change_match = re.search(
        r'<span class="(low|high)?">.*?\(?([\d\.]+)%?\)?\s*([\d,\.]*)</span>',
        row_html
    )
    if change_match:
        change_class, change_percent, change_value = change_match.groups()
        change_percent = float(change_percent)
        change_value = change_value.replace(",", "")
        direction = "افزایش" if change_class == "high" else ("کاهش" if change_class == "low" else "بدون تغییر")
    else:
        change_percent = 0.0
        change_value = "0"
        direction = "بدون تغییر"

    # --- استخراج کمترین و بیشترین و زمان ---
    other_matches = re.findall(r'<td.*?>([\d,\.]+|[\d\s]+)</td>', row_html)
    if len(other_matches) >= 3:
        low, high = other_matches[1], other_matches[2]
        time_ = other_matches[3] if len(other_matches) > 3 else "نامشخص"
    else:
        low, high, time_ = "0", "0", "نامشخص"
    # --- قیمت: ریال یا اعشاری ---
    if "coin"  in url or "chart" in url:  # سکه‌ها
        try:
            price_val = int(float(price_raw.replace(",", "")) / 10)  # تبدیل به تومان
            price_display = "{:,}".format(price_val)
            unit = "تومان"
        except:
            price_display = price_raw
            unit = "تومان"
    else:  # انس‌ها (دلاری)
        try:
            price_val = float(price_raw.replace(",", ""))
            price_display = f"{price_val:,.2f}"
            unit = "دلار"
        except:
            price_display = price_raw
            unit = "دلار"

    # --- پیام نهایی ---
    if change_percent == 0:
        message = f"قیمت {input_name} امروز {price_display} {unit} است و نسبت به دیروز بدون تغییر بوده است. (آخرین بروزرسانی: {time_})"
    else:
        message = f"قیمت {input_name} امروز {price_display} {unit} است و {change_percent}% تغییر داشته که نسبت به دیروز {direction} یافته است. (آخرین بروزرسانی: {time_})"

    return message, price_display.replace(",","")


def get_history_gold2(input_gold: str) -> pd.DataFrame:
    """Fetches historical data for gold/coins from tgju.org API."""

    keywords_path = os.path.join(os.path.dirname(__file__), "data", "golds.json")
    print("keywords_path: ", keywords_path)

    with open(keywords_path, "r", encoding="utf-8") as f:
        indexs = json.load(f)
        
    api_map = indexs["MARKET__HISTORY_URLS"]
    api_map2 = indexs["MARKET_URLS"]
    mapping = indexs["mapping"]
    

    input_name = mapping.get(input_gold, input_gold)
    url = api_map.get(input_name)
    url2 = api_map2.get(input_name)
    table_name = f"gold_{input_name}"

    unit = ""
    if "coin" in url2 or "chart" in url2:  # سکه‌ها
        unit = "تومان"
    else:  # انس‌ها (دلاری)
        unit = "دلار"

    if not url:
        print(f"No API endpoint found for gold type: {input_gold}")
        return pd.DataFrame()

    try:
        response = requests.get(url)
        response.raise_for_status()
        json_data = response.json().get("data", [])
        data_list = []

        change_pattern = re.compile(r'<span class="(low|high)".*?>([\d,]+)<')
        percent_pattern = re.compile(
            r'<span class="(low|high)".*?>([\d\.]+%?)<')

        for item in json_data:
            # Prices are in Rials, convert to Tomans
        
            open_price = float(item[0].replace(",", "")) 
            low_price = float(item[1].replace(",", "")) 
            high_price = float(item[2].replace(",", ""))
            close_price = float(item[3].replace(",", "")) 

            change_html = item[4]
            match = change_pattern.search(change_html)
            price_change = 0.0
            if match:
                status, value = match.groups()
                price_change = float(value.replace(",", "")) 
                if status == "low":
                    price_change *= -1

            percent_html = item[5]
            match = percent_pattern.search(percent_html)
            percent_change_str = "0.0%"
            if match:
                status, value = match.groups()
                percent_change_str = f"{'-' if status == 'low' else '+'}{value}"
            
            if unit == "تومان":
                open_price = open_price / 10
                low_price = low_price / 10
                high_price = high_price / 10
                close_price = close_price / 10
                price_change = price_change / 10



            data_list.append({
                "تاریخ میلادی": item[6],
                "تاریخ شمسی": item[7],
                "بازگشایی": open_price,
                "کمترین قیمت": low_price,
                "بیشترین قیمت": high_price,
                "پایانی": close_price,
                "میزان تغییر": price_change,
                "میزان تغییر درصدی": percent_change_str,
            })

        df = pd.DataFrame(data_list)
        df["تاریخ میلادی"] = df["تاریخ شمسی"].jalali.parse_jalali(
            "%Y/%m/%d").jalali.to_gregorian()
        
        database_store.save_data_to_db(df, table_name)
        return df

    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"Error fetching history for {input_gold}: {e}")
        return pd.DataFrame()


def get_gold_change(input_dataframe: pd.Series, input_symbol: str, input_time: str) :
    """Calculates the percentage change from a past date to today."""
    try:
        gregorian_date = pd.to_datetime(input_time).date()
        shamsi_date_str = jdatetime.date.fromgregorian(
            date=gregorian_date).strftime("%Y/%m/%d")

        past_price = float(input_dataframe["پایانی"])
        _, today_price_str = get_gold_price_tgju(input_symbol)
        today_price = float(today_price_str)

        if past_price == 0:
            return f"قیمت اولیه {input_symbol} صفر بوده و امکان محاسبه تغییرات وجود ندارد.", 0.0

        percent_value = ((today_price - past_price) / past_price) * 100
        rounded_percent = abs(round(percent_value, 2))

        if percent_value > 0:
            direction, emoji = "افزایش", "✅"
        elif percent_value < 0:
            direction, emoji = "کاهش", "🔻"
        else:
            return f"قیمت {input_symbol} از تاریخ {shamsi_date_str} تا امروز تغییری نکرده است.", 0.0
        
        keywords_path = os.path.join(os.path.dirname(__file__), "data", "golds.json")
        with open(keywords_path, "r", encoding="utf-8") as f:
            indexs = json.load(f)
            
        api_map = indexs["MARKET_URLS"]
        mapping = indexs["mapping"]
        

        input_name = mapping.get(input_symbol, input_symbol)
        url = api_map.get(input_name)
    
        unit = ""
        if "coin" in url or "chart" in url:  # سکه‌ها
            unit = "تومان"
        else:  # انس‌ها (دلاری)
            unit = "دلار"


        message = (
            f"{emoji} از تاریخ {shamsi_date_str}، قیمت {input_symbol} {rounded_percent}% {direction} داشته "
            f"و از {past_price:,.0f} به {today_price:,.0f} {unit} رسیده است."
        )
        return message, round(percent_value, 2)

    except (TypeError, ValueError, KeyError) as e:
        return f"خطا در پردازش اطلاعات تغییرات: {e}", 0.0

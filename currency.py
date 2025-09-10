import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import jdatetime
import database_store
import json
import os

def get_currency_price_tgju(input_currency):
    """Fetch current price of a single currency from tgju.org."""
    
    # مسیر فایل mapping ارزها
    keywords_path = os.path.join(os.path.dirname(__file__), "data", "currencies.json")
    with open(keywords_path, "r", encoding="utf-8") as f:
        indexs = json.load(f)
    currency_mapping = indexs["currency_mapping"]
    input_currency_name = currency_mapping.get(input_currency)

    # دریافت صفحه
    currency_link = "https://www.tgju.org/currency"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(currency_link, headers=headers)
    html = response.text

        # پیدا کردن ردیف مربوط به ارز
    row_pattern = re.compile(
        rf'<tr.*?>\s*<th.*?>\s*{re.escape(input_currency_name)}\s*</th>(.*?)</tr>',
        re.DOTALL
    )
    match_row = row_pattern.search(html)
    if not match_row:
        return f"ارز {input_currency_name} پیدا نشد", None

    row_html = match_row.group(1)

    # استخراج قیمت ریال
    price_match = re.search(r'<td.*?>([\d,]+)</td>', row_html)
    price_irr = price_match.group(1) if price_match else "0"

    # استخراج درصد تغییر و مقدار تغییر عددی با توجه به کلاس span
    change_match = re.search(
        r'<span class="(low|high)">\(?([\d\.]+)%?\)?\s*([\d,]*)</span>',
        row_html
    )

    if change_match:
        change_class, change_percent, change_value = change_match.groups()
        change_percent = float(change_percent)
        change_value = change_value.replace(",", "")
        direction = "افزایش" if change_class == "high" else "کاهش"
    else:
        change_percent = 0.0
        change_value = "0"
        direction = "بدون تغییر"

    # استخراج زمان آخرین بروزرسانی
    time_match = re.search(r'<td.*?>(\d{2}:\d{2}:\d{2})</td>', row_html)
    time_ = time_match.group(1) if time_match else "نامشخص"

    # تبدیل ریال به تومان
    try:
        price_tmn = "{:,}".format(int(float(price_irr.replace(",", "")) / 10))
    except ValueError:
        price_tmn = price_irr

    # ساخت پیام
    if change_percent == 0:
        message = f"قیمت {input_currency_name} امروز {price_tmn} تومان است و نسبت به دیروز بدون تغییر بوده است. (آخرین بروزرسانی: {time_})"
    else:
        message = f"قیمت {input_currency_name} امروز {price_tmn} تومان است و {change_percent}% تغییر داشته که نسبت به دیروز {direction} یافته است. (آخرین بروزرسانی: {time_})"

    return message, price_tmn


def get_history_currency2(input_currency):

    table_name = f"currency_{input_currency}"
    data_list = []
    price = ""

    keywords_path = os.path.join(os.path.dirname(__file__), "data", "currencies.json")
    print("keywords_path: ", keywords_path)

    with open(keywords_path, "r", encoding="utf-8") as f:
        indexs = json.load(f)
        
    currency_mapping = indexs["currency_mapping"]
    input_currency_name = currency_mapping.get(input_currency)

    links = indexs["currency_history_data_links"]
    index_link = links.get(input_currency_name)

    response = requests.get(index_link)
    json_data = response.json()["data"]

    pattern = re.compile(r'<span class="(low|high)".*?>(\d+)<')

    pattern2 = re.compile(r'<span class="(low|high)".*?>(\d+\.\d+%)<')

    for data in json_data:
        data_dataframe = {}
        open_price = float(data[0].replace(",", "")) / 10
        lowest_price = float(data[1].replace(",", "")) / 10
        highest_price = float(data[2].replace(",", "")) / 10
        close_price = float(data[3].replace(",", "")) / 10
        price_change = data[4]

        match1 = pattern.search(price_change)
        if match1:
            status = match1.group(1)
            price = match1.group(2)
            price = float(price.replace(",", "")) / 10
            if status == "low":
                price_change = -1 *  price
            else:
                price_change = +1 * price

        percent_change = data[5]

        match2 = pattern2.search(percent_change)
        if match2:
            status = match2.group(1)
            percent = match2.group(2)
            if status == "low":
                percent_change = "-" + percent
            else:
                percent_change = "+" + percent

        miladi_date = data[6]
        shamsi_date = data[7]

        data_dataframe["تاریخ میلادی"] = miladi_date
        data_dataframe["تاریخ شمسی"] = shamsi_date
        data_dataframe["بازگشایی"] = open_price
        data_dataframe["کمترین قیمت"] = lowest_price
        data_dataframe["بیشترین قیمت"] = highest_price
        data_dataframe["پایانی"] = close_price
        data_dataframe["میزان تغییر"] = price_change
        data_dataframe["میزان تغییر درصدی"] = percent_change

        data_list.append(data_dataframe)

    data_frame = pd.DataFrame(data_list)
    data_frame["تاریخ میلادی"] = (data_frame["تاریخ شمسی"].jalali.parse_jalali("%Y/%m/%d").jalali.to_gregorian())

    # دیتای امروز
    today_message, today_price = get_currency_price_tgju(input_currency)
    today_price_float = float(today_price.replace(",", "")) if today_price else None
    today_shamsi = jdatetime.date.today().strftime("%Y/%m/%d")
    today_miladi = pd.Timestamp.today().strftime("%Y-%m-%d 00:00:00")

    today_df = pd.DataFrame([{
        "تاریخ میلادی": today_miladi,
        "تاریخ شمسی": today_shamsi,
        "پایانی": today_price_float
    }])

    final_df = pd.concat([today_df,data_frame], ignore_index=True)

    # تبدیل تاریخ‌ها به string برای SQLite
    final_df["تاریخ میلادی"] = final_df["تاریخ میلادی"].astype(str)
    final_df["تاریخ شمسی"] = final_df["تاریخ شمسی"].astype(str)

    database_store.save_data_to_db(final_df, table_name)

    return final_df


def get_currency_change(input_dataframe, input_symbol, input_time):
    try:
        gregorian_date = pd.to_datetime(input_time).date()
        shamsi_date_str = jdatetime.date.fromgregorian(date=gregorian_date).strftime(
            "%Y/%m/%d"
        )

        past_data = input_dataframe.copy()
        past_price = past_data["پایانی"]
        today_price = float(get_currency_price_tgju(input_symbol)[1].replace(",", ""))

        if past_price == 0:
            return (
                f"قیمت اولیه {input_symbol} صفر بوده و امکان محاسبه تغییرات وجود ندارد."
            )

        percent_value = ((today_price - past_price) / past_price) * 100
        rounded_percent = abs(round(percent_value, 2))

        if percent_value > 0:
            return f"✅ از تاریخ {shamsi_date_str}، قیمت {input_symbol} {rounded_percent}% افزایش داشته و از {past_price:,.0f} به {today_price:,.0f} تومان رسیده است.",round(percent_value, 2)

        elif percent_value < 0:
            return f"🔻 از تاریخ {shamsi_date_str}، قیمت {input_symbol} {rounded_percent}% کاهش داشته و از {past_price:,.0f} به {today_price:,.0f} تومان رسیده است.",round(percent_value, 2)

        else:
            return f" قیمت {input_symbol} از تاریخ {shamsi_date_str} تا امروز تغییری نکرده و روی {today_price:,.0f} تومان ثابت مانده است.",round(percent_value, 2)

    except Exception as e:
        return f"خطا در پردازش اطلاعات: {e}"

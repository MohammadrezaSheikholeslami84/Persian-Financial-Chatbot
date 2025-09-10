import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import jdatetime
import database_store
import financial_core
import os
import json
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime


# تابع کمکی برای تبدیل رشته به عدد
def parse_number(text: str) -> float:
    text = text.replace(",", "").strip()
    if "میلیون" in text:
        return float(text.replace("میلیون", "").strip()) * 1_000_000
    elif "هزار" in text:
        return float(text.replace("هزار", "").strip()) * 1_000
    else:
        try:
            return float(text)
        except:
            return text  # اگر نشد همون متن برگرده


def get_iran_index_data(input_index):
    """Fetch current Iranian index data from databourse.ir"""

    # نقشه نام‌های ورودی به نام‌های سایت
    indexs = {
        "شاخص کل": "شاخص کل",
        "شاخص بورس": "شاخص کل",
        "شاخص فرابورس": "شاخص کل فرابورس",
        "شاخص هم وزن": "شاخص قیمت (هم وزن)",
    }
    index_name = indexs.get(input_index)
    index_link = "https://databourse.ir/indices"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    }

    # الگوی رنگ (سبز/قرمز) در سایت
    pattern = re.compile(r'<td class="indexPercent (green|red)">')

    # درخواست به سایت
    response = requests.get(index_link, headers=headers, verify=False)
    if response.status_code != 200:
        return "❌ مشکلی در اتصال به سایت پیش آمد.", None

    soup = BeautifulSoup(response.text, "html.parser")
    body = soup.find("tbody")
    each_index = body.find_all("tr")
    each_data = [index.find_all("td") for index in each_index]

    for data in each_data:
        if data[0].text.strip() == index_name:

            index_name = data[0].text.strip()
            index_price = float(data[1].text.replace(",", ""))
            index_change = float(data[2].text.replace(",", ""))

            # پردازش درصد تغییر: حذف پرانتز و تبدیل به float
            change_text = data[3].text.strip()  # مثال: "(-0.90)" یا "(0.90)"
            change_text = (
                change_text.replace("(", "").replace(")", "").replace(",", "").strip()
            )
            try:
                index_change_percentage = float(change_text)
            except:
                index_change_percentage = 0.0

            index_change_direction = "green" if index_change_percentage >= 0 else "red"
            direction_emoji = "📈" if index_change_direction == "green" else "📉"

            index_time_str = data[4].text.strip()
            try:
                index_time = datetime.strptime(index_time_str, "%H:%M:%S").strftime("%H:%M:%S")
            except:
                index_time = index_time_str

            output = (
                f"{direction_emoji} {index_name} برابر {index_price:,.0f} واحد است و نسبت به روز گذشته "
                f"{abs(index_change):,.0f} واحد {'افزایش' if index_change_direction == 'green' else 'کاهش'} داشته "
                f"که معادل {abs(index_change_percentage):.2f}% است. "
                f"این اطلاعات در ساعت {index_time} ثبت شده است."
            )

            return output, index_price

    return "❌ شاخص موردنظر پیدا نشد.", None

def get_iran_index_data2(index_name_input: str) -> str:
    url = "https://www.shakhesban.com/markets/index"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

     # مسیر فایل mapping ارزها
    keywords_path = os.path.join(os.path.dirname(__file__), "data", "iran_index.json")
    with open(keywords_path, "r", encoding="utf-8") as f:
        indexs = json.load(f)
    index_name_mapping = indexs["INDEX_NAME_MAPPING"]
    index_name_input = index_name_mapping.get(index_name_input)


    print(index_name_input)

    rows = soup.find_all("tr")
    data = []
    for row in rows:
        if row.find("td", {"data-col": "title"}):
            change_perc_raw = row.find("td", {"data-col": "change_percentage"}).get_text(strip=True)
            span = row.find("td", {"data-col": "change_percentage"}).find("span")
            if "change-up" in span.get("class", []):
                change_perc = "+" + change_perc_raw + "%"
            elif "change-down" in span.get("class", []):
                change_perc = "-" + change_perc_raw + "%"
            else:
                change_perc = change_perc_raw + "%"

            row_data = {
                "title": row.find("td", {"data-col": "title"}).get_text(strip=True),
                "market_fa": row.find("td", {"data-col": "market_fa"}).get_text(strip=True),
                "flow_title": row.find("td", {"data-col": "flow_title"}).get_text(strip=True),
                "value": row.find("td", {"data-col": "value"}).get_text(strip=True),
                "change": row.find("td", {"data-col": "change"}).get_text(strip=True),
                "change_percentage": change_perc,
                "time": row.find("td", {"data-col": "time"}).get_text(strip=True),
                "min": row.find("td", {"data-col": "min"}).get_text(strip=True),
                "max": row.find("td", {"data-col": "max"}).get_text(strip=True),
            }
            data.append(row_data)

    df = pd.DataFrame(data)

    row = df[df["title"] == index_name_input]
    if row.empty:
        return f"❌ شاخص '{index_name_input}' یافت نشد."

    row = row.iloc[0]

    # تبدیل داده‌ها به عدد
    index_name = row["title"]
    index_price = parse_number(row["value"])
    index_change = parse_number(row["change"])
    index_change_percentage = float(
        row["change_percentage"].replace("%", "").replace("+", "").replace("-", "")
    )

    if str(row["change_percentage"]).startswith("+"):
        index_change_direction = "green"
        direction_emoji = "🟢"
    elif str(row["change_percentage"]).startswith("-"):
        index_change_direction = "red"
        direction_emoji = "🔴"
    else:
        index_change_direction = "neutral"
        direction_emoji = "⚪️"

    index_time = row["time"]

    output = (
        f"{direction_emoji} {index_name} برابر {index_price:,.0f} واحد است و نسبت به روز گذشته "
        f"{abs(index_change):,.0f} واحد {'افزایش' if index_change_direction == 'green' else 'کاهش'} داشته "
        f"که معادل {abs(index_change_percentage):.2f}% است. "
        f"این اطلاعات در تاریخ {index_time} ثبت شده است."
    )

    return output,index_price


def get_iran_index_change(input_dataframe, input_symbol, input_time):     
        gregorian_date = pd.to_datetime(input_time).date()
        shamsi_date_str = jdatetime.date.fromgregorian(date=gregorian_date).strftime("%Y/%m/%d")
        past_data = input_dataframe.copy()
        past_price = float(past_data["پایانی"].replace(",", ""))
        today_index_result = get_iran_index_data(input_symbol)[1]
        
        print(today_index_result)
        if today_index_result is None:
            return f"❌ شاخص امروز برای {input_symbol} یافت نشد."
        
        today_price = float(today_index_result)

        if past_price == 0:
            return (f"قیمت اولیه {input_symbol} صفر بوده و امکان محاسبه تغییرات وجود ندارد.")

        percent_value = ((today_price - past_price) / past_price) * 100
        rounded_percent = abs(round(percent_value, 2))

        print(f"Past Price: {past_price}, Today Price: {today_price}, Percent Change: {percent_value}")

        if percent_value > 0:
            return f"✅ از تاریخ {shamsi_date_str}، قیمت {input_symbol} {rounded_percent} درصد افزایش داشته و از {past_price:,.0f} به {today_price:,.0f} واحد رسیده است.",round(percent_value, 2)

        elif percent_value < 0:
            return f"🔻 از تاریخ {shamsi_date_str}، قیمت {input_symbol} {rounded_percent} درصد کاهش داشته و از {past_price:,.0f} به {today_price:,.0f} واحد رسیده است.",round(percent_value, 2)

        else:
            return f" قیمت {input_symbol} از تاریخ {shamsi_date_str} تا امروز تغییری نکرده و روی {today_price:,.0f} واحد ثابت مانده است.",round(percent_value, 2)



def get_history_iran_index2(input_currency):
    table_name = f"iran_index_{input_currency}"
    data_list = []

    indexs = {
        "شاخص کل": financial_core.url_converter("ش-کل-بورس", "index"),
        "شاخص بورس": financial_core.url_converter("ش-کل-بورس", "index"),
        "شاخص فرابورس": financial_core.url_converter("ش-کل-فرابورس", "index"),
        "شاخص هم وزن": financial_core.url_converter("ش-کل-هم-وزن", "index"),
        "شاخص بورس ایران": financial_core.url_converter("ش-کل-بورس", "index"),
        "بورس ایران": financial_core.url_converter("ش-کل-بورس", "index"),
        "بورس": financial_core.url_converter("ش-کل-بورس", "index"),
    }

    index_link = indexs.get(input_currency)

    response = requests.get(index_link)
    json_data = response.json()["data"]

    pattern = re.compile(r"(\d+.\d+)")

    for data in json_data:
        data_dataframe = {}

        shamsi_date = data[0]
        close_price = data[1]
        lowest_price = data[2].replace(",", "")
        highest_price = data[3].replace(",", "")

        if "میلیون" in close_price:

            match1 = pattern.search(close_price)
            match2 = pattern.search(lowest_price)
            match3 = pattern.search(highest_price)

            if match1:
                close_price = float(match1.group(1)) * 1000000
            if match2:
                lowest_price = float(match2.group(1)) * 1000000
            if match3:
                highest_price = float(match3.group(1)) * 1000000

        data_dataframe["تاریخ شمسی"] = shamsi_date
        data_dataframe["کمترین قیمت"] = lowest_price
        data_dataframe["بیشترین قیمت"] = highest_price
        data_dataframe["پایانی"] = close_price

        data_list.append(data_dataframe)

    data_frame = pd.DataFrame(data_list)
    data_frame["تاریخ میلادی"] = (
        data_frame["تاریخ شمسی"].jalali.parse_jalali("%Y/%m/%d").jalali.to_gregorian()
    )
    cols_to_move = ["تاریخ میلادی"]
    new_cols = cols_to_move + [
        col for col in data_frame.columns if col not in cols_to_move
    ]
    data_frame = data_frame[new_cols]
    database_store.save_data_to_db(data_frame, table_name)
    return data_frame

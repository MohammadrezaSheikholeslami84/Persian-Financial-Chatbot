import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import jdatetime
import database_store
import os
import json

def get_cryptocurrency_price_tgju(input_cryptocurrency):
    url = "https://www.tgju.org/crypto"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Error fetching the page:", response.status_code)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    tbody = soup.find("tbody", {"class": "lg:tgcss-divide-x lg:tgcss-divide-x-reverse"})
    rows = tbody.find_all("tr", {"data-market-coding": "true"})

    data_list = []
    for row in rows:
        try:
            # نام فارسی
            name_fa = row.find("div", class_="tgcss-font-semibold").get_text(strip=True)
            # نماد ارز
            symbol = row.find("div", class_="tgcss-font-medium").get_text(strip=True)
            # قیمت تتـر
            price_usdt = row.find("div", {"data-market-name": "p"}).get_text(strip=True)
            # نام انگلیسی برای پیدا کردن قیمت ریال
            eng_name_span = row.find("span", class_="original-title-en")
            eng_name = eng_name_span.get_text(strip=True).lower() if eng_name_span else None

            # قیمت ریال
            price_irr_div = row.find("div", {"data-market-p": f"crypto-{eng_name}-irr"}) if eng_name else None
            price_irr = price_irr_div.get_text(strip=True) if price_irr_div else None

            # تغییر عددی
            change_value_div = row.find("div", {"data-market-name": "dv"})
            change_value = change_value_div.get_text(strip=True) if change_value_div else None

            # تغییر درصدی
            change_percent_div = row.find("div", {"data-market-name": "dp"})
            change_percent = change_percent_div.get_text(strip=True).replace("%", "").strip() if change_percent_div else "0"

            # تشخیص افزایش یا کاهش
            change_type = None
            if change_value_div:
                classes = change_value_div.get("class", [])
                if any("emerald" in c for c in classes):  # سبز
                    change_type = "Increase"
                elif any("rose" in c for c in classes):  # قرمز
                    change_type = "Decrease"

            # زمان بروزرسانی
            time_td = row.find("td", {"data-label": "زمان بروزرسانی"})
            time_ = time_td.get_text(strip=True) if time_td else None

            try:
                price_numeric = int(float(price_irr.replace(",", "").strip()) / 10)
                price_irr = "{:,}".format(price_numeric)
            except ValueError:
                price_irr = price_irr

            # پیام متنی
            try:
                change_percent_num = float(change_percent.replace(",", "").replace("−", "-"))
            except:
                change_percent_num = 0.0

            if change_type == "Increase":
                direction = "افزایش"
            elif change_type == "Decrease":
                direction = "کاهش"
            else:
                direction = "بدون تغییر"

            if change_percent_num == 0:
                message = f"قیمت {name_fa} ({symbol}) امروز {price_usdt} دلار و معادل {price_irr} تومان است و نسبت به دیروز بدون تغییر بوده است. (آخرین بروزرسانی: {time_})"
            else:
                message = f"قیمت {name_fa} ({symbol}) امروز {price_usdt} دلار و معادل {price_irr} تومان است و {abs(change_percent_num)} درصد تغییر داشته که نسبت به دیروز {direction} یافته است. (آخرین بروزرسانی: {time_})"

            data_list.append({
                "Name": name_fa,
                "Symbol": symbol,
                "Price_USDT": price_usdt,
                "Price_IRR": price_irr,
                "Change_Value": change_value,
                "Change_Percent": change_percent,
                "Change_Type": change_type,
                "Update_Time": time_,
                "Message": message   # ⬅️ پیام آماده
            })
        
        except Exception as e:
            print("Error parsing row:", e)
            continue
    

    df = pd.DataFrame(data_list)
    if input_cryptocurrency in df["Name"].values:
        message = str(df[df["Name"] == input_cryptocurrency]["Message"].values[0])
        current_price = str(df[df["Name"] == input_cryptocurrency]["Price_USDT"].values[0])
        return message, current_price, df
    else:
        return f"ارز {input_cryptocurrency} پیدا نشد", None    


def get_history_cryptocurrency2(input_cryptocurrency):
    
    table_name = f"cryptocurrency_{input_cryptocurrency}"
    data_list = []
    price = ""

    
    keywords_path = os.path.join(os.path.dirname(__file__), "data", "cryptocurrencies.json")
    print("keywords_path: ", keywords_path)

    with open(keywords_path, "r", encoding="utf-8") as f:
        indexs = json.load(f)
        
    links = indexs["cryptocurrency_history_data_links"]
    index_link = links.get(input_cryptocurrency)

    response = requests.get(index_link)
    json_data = response.json()["data"]

    pattern = re.compile(r'<span class="(low|high)".*?>(\d+\.\d+)<')

    pattern2 = re.compile(r'<span class="(low|high)".*?>(\d+\.\d+%)<')

    for data in json_data:
        data_dataframe = {}
        open_price = float(data[0].replace(",", "")) 
        lowest_price = float(data[1].replace(",", ""))
        highest_price = float(data[2].replace(",", ""))
        close_price = float(data[3].replace(",", ""))
        price_change = data[4]

        match1 = pattern.search(price_change)
        if match1:
            status = match1.group(1)
            price = match1.group(2)
            price = float(price.replace(",", ""))

            if status == "low":
                price_change = -1 * price
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
    today_message, today_price, today_df_full = get_cryptocurrency_price_tgju(input_cryptocurrency)
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


def get_cryptocurrency_change(input_dataframe,input_symbol, input_time):
    try:
        gregorian_date = pd.to_datetime(input_time).date()
        shamsi_date_str = jdatetime.date.fromgregorian(date=gregorian_date).strftime("%Y/%m/%d")

        past_data = input_dataframe.copy()
        past_price = past_data["پایانی"]
        today_price = float(get_cryptocurrency_price_tgju(input_symbol)[1].replace(",", ""))

        if past_price == 0:
            return f"قیمت اولیه {input_symbol} صفر بوده و امکان محاسبه تغییرات وجود ندارد."

        percent_value = ((today_price - past_price) / past_price) * 100
        rounded_percent = abs(round(percent_value, 2))

        if percent_value > 0:
            return f"✅ از تاریخ {shamsi_date_str}، قیمت {input_symbol} {rounded_percent}% افزایش داشته و از {past_price:,.0f} به {today_price:,.0f} دلار رسیده است.",round(percent_value, 2)

        elif percent_value < 0:
            return f"🔻 از تاریخ {shamsi_date_str}، قیمت {input_symbol} {rounded_percent}% کاهش داشته و از {past_price:,.0f} به {today_price:,.0f} دلار رسیده است.",round(percent_value, 2)

        else:
            return f" قیمت {input_symbol} از تاریخ {shamsi_date_str} تا امروز تغییری نکرده و روی {today_price:,.0f} دلار ثابت مانده است.",round(percent_value, 2)

    except Exception as e:
        return f"خطا در پردازش اطلاعات: {e}"

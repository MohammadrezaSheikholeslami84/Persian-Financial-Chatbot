import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import jdatetime
import database_store
import financial_core


def get_iran_symbol_data(input_symbol):
    """Fetch current Iranian symbol data from BrsApi."""
    api_key = "FreeBvt6cnOYtMgfj8GQP5GSuIy8LUh5"
    url = f"https://BrsApi.ir/Api/Tsetmc/AllSymbols.php?key={api_key}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        for symbols in data:
            symbol_name = symbols.get("l18", "")
            company_name = symbols.get("l30", "")
            time = symbols.get("time", "")
            price = "{:,}".format(float(symbols.get("pc", 0)) / 10)
            price_change_percentage = float(symbols.get("pcp", 0))

            if symbol_name.strip().lower() == input_symbol.strip().lower():
                direction = "بدون تغییر"
                if price_change_percentage > 0:
                    direction = "افزایش"
                elif price_change_percentage < 0:
                    direction = "کاهش"

                if price_change_percentage == 0:
                    message = (
                        f"قیمت نماد {company_name} ({input_symbol}) برابر {price} تومان است "
                        f"و نسبت به دیروز بدون تغییر بوده است. (⏰ زمان: {time})"
                    )
                else:
                    message = (
                        f"قیمت نماد {company_name} ({input_symbol}) برابر {price} تومان است و "
                        f"{abs(price_change_percentage)} درصد تغییر داشته که نسبت به دیروز {direction} یافته است. "
                        f"(⏰ زمان: {time})"
                    )
                return message, price

        return {"message": "Symbol not found"}

    except Exception as e:
        return {"error": str(e)}


def get_iran_symbol_data2(input_symbol, timeout=5):
    
    """Fetch current Iranian symbol data from shakhesban."""

    input_symbol = input_symbol.strip()
    session = requests.Session()  
    page = 1
    
    pattern_row = re.compile(
        rf'(<tr\b[^>]*\bdata-symbol=[\'"]{re.escape(input_symbol)}[\'"][^>]*>.*?</tr>)',
        re.S | re.I
    )

    
    td_tag_pattern = re.compile(r'(<td\b[^>]*>.*?</td>)', re.S | re.I)
    data_col_re = re.compile(r'data-col=[\'"]([^\'"]+)[\'"]', re.I)
    data_val_re = re.compile(r'data-val=[\'"]([^\'"]*)[\'"]', re.I)

    while True:
        url = f"https://www.shakhesban.com/stocks/list-data?limit=100&page={page}&order_col=info.last_date&order_dir=desc&market=stock"
        resp = session.get(url)
        data = resp.json()
        tbody_html = data.get("tbody", "")

        match = pattern_row.search(tbody_html)
        if not match:
            if not data.get("is_more"):
                break
            page += 1
            continue

        tr_html = match.group(1)

        soup = BeautifulSoup(tr_html, "html.parser")
        row_data = {}
        for td in soup.find_all("td"):
            col = td.get("data-col")
            val = td.get("data-val")
            if col:
                if val is None:
                    val = td.get_text(strip=True)
                row_data[col] = val

       
        if not row_data:
            for td_html in td_tag_pattern.findall(tr_html):
                col_m = data_col_re.search(td_html)
                val_m = data_val_re.search(td_html)
                if col_m:
                    col = col_m.group(1)
                    val = val_m.group(1) if val_m else re.sub(r'<.*?>', '', td_html).strip()
                    row_data[col] = val

       
        price_raw = (
            row_data.get("info.last_price.PClosing")
            or row_data.get("info.last_trade.PDrCotVal")
            or row_data.get("info.PriceYesterday")
            or "0"
        )
        try:
            # تبدیل به عدد و تقسیم بر 10 (اگه لازم باشه)
            price = int(str(price_raw).replace(",", "")) // 10
            price = "{:,}".format(price)
        except Exception:
            price = None

        pct_raw = (
            row_data.get("info.last_price.closing_change_percentage")
            or row_data.get("info.last_trade.last_change_percentage")
            or "0"
        )
        try:
            price_change_percentage = float(str(pct_raw).replace("%", "").replace(",", ""))
        except Exception:
            price_change_percentage = 0.0

        title = row_data.get("info.title") or row_data.get("info.symbol") or input_symbol

        if price_change_percentage > 0:
            direction = "افزایش"
        elif price_change_percentage < 0:
            direction = "کاهش"
        else:
            direction = "بدون تغییر"

        if price_change_percentage == 0 or price is None:
            message = f"قیمت نماد {title} ({input_symbol}) برابر {price} تومان است و نسبت به دیروز بدون تغییر بوده است."
        else:
            message = (
                f"قیمت نماد {title} ({input_symbol}) برابر {price} تومان است و "
                f"{abs(price_change_percentage)} درصد تغییر داشته که نسبت به دیروز {direction} یافته است."
            )

        return message, price
    
    return get_iran_symbol_data2(input_symbol)
   # return f"نماد {input_symbol} پیدا نشد.", None, None


def get_iran_symbol_change(input_dataframe,input_symbol, input_time):
    try:
        gregorian_date = pd.to_datetime(input_time).date()
        shamsi_date_str = jdatetime.date.fromgregorian(date=gregorian_date).strftime("%Y/%m/%d")
        
        past_data = input_dataframe.copy()
        past_price = past_data["پایانی"]
        
        today_price = float(get_iran_symbol_data(input_symbol)[1].replace(",", ""))

        if past_price == 0:
            return (f"قیمت اولیه {input_symbol} صفر بوده و امکان محاسبه تغییرات وجود ندارد.")

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


def get_history_iran_symbol2(input_currency):
    table_name = f"iran_symbol_{input_currency}"
    data_list = []

    index_link = financial_core.url_converter(input_currency, "stock")

    response = requests.get(index_link)
    json_data = response.json()["data"]

    pattern1 = re.compile(r'<span class="label">تعداد:</span><span class="value">(\d+\.*\d+)')
    pattern2 = re.compile(r'<span class="label">حجم:</span><span class="value">(\d+\.\d+)')
    pattern3 = re.compile(r'<span class="label">ارزش:</span><span class="value">(\d+\.\d+)')

    pattern4 = re.compile(r'<span class="label">اولین:</span><span class="value">(\d+,\d+)')
    pattern5 = re.compile(r'<span class="label">کمترین:</span><span class="value">(\d+,\d+)')
    pattern6 = re.compile(r'<span class="label">بیشترین:</span><span class="value">(\d+,\d+)')

    pattern7 = re.compile(r'<span class="label">قیمت:</span><span class="value">(\d+,\d+)')
    pattern8 = re.compile(r'<span class="label">تغییر:</span><span class="value"><span class="change change-(up|down|no change)">(\d+,*\d+\.\d+)')
    pattern9 = re.compile(r'<span class="label">درصد تغییر:</span><span class="value"><span class="change change-(up|down|no) change-percentage">(\d+\.\d+)')

    quantity = ""
    volume = ""
    value = ""
    first_price = ""
    lowest_price = ""
    highest_price = ""
    last_prices_price = ""
    last_prices_change = ""
    last_prices_percentage_change = ""
    close_prices_price = ""
    close_prices_change = ""
    close_prices_percentage_change = ""

    for data in json_data:

        data_dataframe = {}
        shamsi_date = data[0]
        transactions = data[1]
        prices = data[2]
        last_prices = data[3]
        close_prices = data[4]

        # print(last_prices)

        match1 = pattern1.search(transactions)
        match2 = pattern2.search(transactions)
        match3 = pattern3.search(transactions)

        match4 = pattern4.search(prices)
        match5 = pattern5.search(prices)
        match6 = pattern6.search(prices)

        match7 = pattern7.search(last_prices)
        match8 = pattern8.search(last_prices)
        match9 = pattern9.search(last_prices)

        match10 = pattern7.search(close_prices)
        match11 = pattern8.search(close_prices)
        match12 = pattern9.search(close_prices)

        if match1:
            quantity = match1.group(1)
        if match2:
            volume = float(match2.group(1)) * 1000000
        if match3:
            value = float(match3.group(1)) * 1000000000

        if match4:
            first_price = float(match4.group(1).replace(",", ""))/10
        if match5:
            lowest_price = float(match5.group(1).replace(",", ""))/10
        if match6:
            highest_price = float(match6.group(1).replace(",", ""))/10

        if match7:
            last_prices_price =  float(match7.group(1).replace(",", ""))/10

        if match8:
            status = match8.group(1)
            last_prices_change = match8.group(2)
            last_prices_change = float(last_prices_change.replace(",", "")) / 10

            if status == "down":
                last_prices_change = -1 * last_prices_change
            elif status == "up":
                last_prices_change = +1 * last_prices_change

        if match9:
            status = match9.group(1)
            last_prices_percentage_change = float(match9.group(2))
            if status == "down":
                last_prices_percentage_change = -1 * last_prices_percentage_change
            elif status == "up":
                last_prices_percentage_change = +1 * last_prices_percentage_change

        if match10:
            close_prices_price = float(match10.group(1).replace(",", ""))/10

        if match11:
            status = match11.group(1)
            close_prices_change = match11.group(2)
            close_prices_change = float(close_prices_change.replace(",", "")) / 10
            if status == "down":
                close_prices_change = -1 *  close_prices_change
            elif status == "up":
                close_prices_change = +1 * close_prices_change

        if match12:
            status = match12.group(1)
            close_prices_percentage_change = match12.group(2)
            if status == "down":
                close_prices_percentage_change = "-" + close_prices_percentage_change + "%"
            elif status == "up":
                close_prices_percentage_change = ( "+" + close_prices_percentage_change + "%")

        data_dataframe = {}
        data_dataframe["تاریخ شمسی"] = shamsi_date

        data_dataframe["تعداد"] = quantity
        data_dataframe["حجم"] = volume
        data_dataframe["ارزش"] = value

        data_dataframe["بازگشایی"] = first_price
        data_dataframe["کمترین قیمت"] = lowest_price
        data_dataframe["بیشترین قیمت"] = highest_price

        data_dataframe["قیمت"] = last_prices_price
        data_dataframe[" میزان تغییر اخرین"] = last_prices_change
        data_dataframe["میزان تغییر درصدی اخرین"] = last_prices_percentage_change

        data_dataframe["پایانی"] = close_prices_price
        data_dataframe["میزان تغییر"] = close_prices_change
        data_dataframe["میزان تغییر درصدی"] = close_prices_percentage_change
        data_list.append(data_dataframe)

    data_frame = pd.DataFrame(data_list)
    data_frame["تاریخ میلادی"] = (data_frame["تاریخ شمسی"].jalali.parse_jalali("%Y/%m/%d").jalali.to_gregorian())

    cols_to_move = ["تاریخ میلادی"]
    new_cols = cols_to_move + [col for col in data_frame.columns if col not in cols_to_move]
    data_frame = data_frame[new_cols]
    database_store.save_data_to_db(data_frame, table_name)
    
    return data_frame

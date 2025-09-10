import pandas as pd
import requests
import jdatetime
import database_store
from datetime import datetime


def format_stock_message(input_company, today, today_close, change_percent):
    today_dt = datetime.strptime(today, "%Y-%m-%d")

    today_jalali = jdatetime.date.fromgregorian(date=today_dt.date())
    jalali_date = f"{today_jalali.year}/{today_jalali.month:02}/{today_jalali.day:02}"

    gregorian_date = today_dt.strftime("%d/%m/%Y")

    if change_percent > 0:
        change_text = f"که افزایش {abs(change_percent):.2f}% نسبت به روز قبل داشته است."
    elif change_percent < 0:
        change_text = f"که کاهش {abs(change_percent):.2f}% نسبت به روز قبل داشته است."
    else:
        change_text = "و نسبت به روز قبل بدون تغییر بوده است."

    return (
        f"قیمت سهام {input_company} در تاریخ {jalali_date} (معادل {gregorian_date}) برابر با {today_close:.2f} دلار بوده است.\n"
        f"{change_text}"
    )


def get_america_stock_price(input_company):
    """Fetch current American stock price from Alpha Vantage."""

    companies = {
        "اپل": "AAPL",
        "گوگل": "GOOGL",
        "آمازون": "AMZN",
        "مایکروسافت": "MSFT",
        "تسلا": "TSLA",
    }

    symbol = companies.get(input_company)
    if not symbol:
        return "❌ نام شرکت معتبر نیست!"

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": "E1YC4NIVQ9K96G65",
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "Time Series (Daily)" not in data:
        return f"⛔️ داده‌ای برای نماد {symbol} پیدا نشد یا API محدود شده."

    time_series = data["Time Series (Daily)"]
    sorted_dates = sorted(time_series.keys(), reverse=True)

    if len(sorted_dates) < 2:
        return "⛔️ تعداد روزهای معاملاتی کافی نیست."

    today = sorted_dates[0]
    yesterday = sorted_dates[1]

    today_close = float(time_series[today]["4. close"])
    yesterday_close = float(time_series[yesterday]["4. close"])

    change_percent = ((today_close - yesterday_close) / yesterday_close) * 100

    output = format_stock_message(input_company, today, today_close, change_percent)
    return output, today_close


def get_history_america_stock2(input_company):
    """Fetch current American stock price from Alpha Vantage."""

    table_name = f"america_stock_{input_company}"

    companies = {
        "اپل": "AAPL",
        "گوگل": "GOOGL",
        "آمازون": "AMZN",
        "امازون": "AMZN",
        "مایکروسافت": "MSFT",
        "تسلا": "TSLA",
    }

    symbol = companies.get(input_company)
    if not symbol:
        return "❌ نام شرکت معتبر نیست!"

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": "E1YC4NIVQ9K96G65",
        "outputsize": "full",
    }

    response = requests.get(url, params=params)
    data = response.json()

    time_series = data["Time Series (Daily)"]
    sorted_dates = sorted(time_series.keys(), reverse=True)

    df = pd.DataFrame.from_dict(time_series, orient="index").reset_index()
    df = df.rename(
        columns={
            "index": "تاریخ میلادی",
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "پایانی",
            "5. volume": "Volume",
        }
    )
    df["تاریخ میلادی"] = pd.to_datetime(df["تاریخ میلادی"])
    df["تاریخ شمسی"] = df["تاریخ میلادی"].apply(
        lambda x: jdatetime.date.fromgregorian(date=x.date()).strftime("%Y/%m/%d")
    )

    df = df.astype(
        {
            "Open": "float",
            "High": "float",
            "Low": "float",
            "پایانی": "float",
            "Volume": "int",
        }
    )
    database_store.save_data_to_db(df, table_name)
    return df


def get_america_stock_change(input_dataframe, input_symbol, input_time):
    try:
        gregorian_date = pd.to_datetime(input_time).date()
        shamsi_date_str = jdatetime.date.fromgregorian(date=gregorian_date).strftime(
            "%Y/%m/%d"
        )

        past_data = input_dataframe.copy()
        past_price = float(past_data["پایانی"])
        today_price = float(get_america_stock_price(input_symbol)[1])

        if past_price == 0:
            return (
                f"قیمت اولیه {input_symbol} صفر بوده و امکان محاسبه تغییرات وجود ندارد."
            )

        percent_value = ((today_price - past_price) / past_price) * 100
        rounded_percent = abs(round(percent_value, 2))

        if percent_value > 0:
            return f"✅ از تاریخ {shamsi_date_str}، قیمت {input_symbol} {rounded_percent} درصد افزایش داشته و از {past_price:,.0f} به {today_price:,.0f} دلار رسیده است.",round(percent_value, 2)

        elif percent_value < 0:
            return f"🔻 از تاریخ {shamsi_date_str}، قیمت {input_symbol} {rounded_percent} درصد کاهش داشته و از {past_price:,.0f} به {today_price:,.0f} دلار رسیده است.",round(percent_value, 2)

        else:
            return f" قیمت {input_symbol} از تاریخ {shamsi_date_str} تا امروز تغییری نکرده و روی {today_price:,.0f} دلار ثابت مانده است.",round(percent_value, 2)

    except Exception as e:
        return f"خطا در پردازش اطلاعات: {e}"

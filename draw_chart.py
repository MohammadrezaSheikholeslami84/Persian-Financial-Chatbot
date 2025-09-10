import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import jdatetime
import io
from matplotlib.ticker import FuncFormatter
import arabic_reshaper
from bidi.algorithm import get_display
import matplotlib.font_manager as fm
import database_store
import requests
import os
import currency
import gold
import cryptocurrency
import iran_index
import iran_symbol
import america_stock
import matplotlib

matplotlib.use("Agg")


def setup_persian_font():
    """
    Downloads and sets up the Vazirmatn Persian font for use in matplotlib charts.
    """
    font_name = "Vazirmatn-Regular.ttf"
    if not os.path.exists(font_name):
        print(f"Downloading Persian font: {font_name}...")
        try:
            url = "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Regular.ttf"

            response = requests.get(url)
            response.raise_for_status()

            with open(font_name, "wb") as f:
                f.write(response.content)
            print("Font downloaded successfully.")

        except requests.RequestException as e:
            print(
                f"Failed to download font. Please add '{font_name}' manually. Error: {e}"
            )
            return None

    return font_name


def create_price_chart(dataframe: pd.DataFrame, title: str, ylabel: str) -> io.BytesIO:
    dataframe = dataframe.copy()
    dataframe["تاریخ میلادی"] = pd.to_datetime(
        dataframe["تاریخ میلادی"], errors="coerce"
    )
    dataframe["پایانی"] = pd.to_numeric(dataframe["پایانی"], errors="coerce")
    dataframe = dataframe.dropna(subset=["پایانی"])
    dataframe = dataframe.dropna(subset=["تاریخ میلادی"])

    if dataframe.empty:
        raise ValueError("دیتافریم ورودی برای رسم نمودار خالی است.")

    font_path = setup_persian_font()
    if not font_path:
        raise RuntimeError("فونت فارسی برای رسم نمودار یافت نشد.")
    font_prop = fm.FontProperties(fname=font_path, size=12)

    def persian_text(text):
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(
        dataframe["تاریخ میلادی"],
        dataframe["پایانی"],
        marker=".",
        linestyle="-",
        markersize=8,
        color="#007acc",
    )
    y_min, y_max = dataframe["پایانی"].min(), dataframe["پایانی"].max()
    margin = (y_max - y_min) * 0.05
    ax.set_ylim(y_min - margin, y_max + margin)

    ax.fill_between(
        dataframe["تاریخ میلادی"], dataframe["پایانی"], color="#007acc", alpha=0.1
    )

    ax.set_title(persian_text(title),
                 fontproperties=font_prop, fontsize=16, pad=20)
    ax.set_xlabel(persian_text("تاریخ"), fontproperties=font_prop)
    ax.set_ylabel(persian_text(ylabel), fontproperties=font_prop)

    def dynamic_price_formatter(y, pos):
        if y >= 1_000_000_000:
            val = f"{y / 1_000_000_000:.1f} B"
        elif y >= 1_000_000:
            val = f"{y / 1_000_000:.1f} M"
        elif y >= 1_000:
            val = f"{int(y/1000):,} K"
        else:
            val = f"{int(y):,}"
        return persian_text(val.replace(".0", ""))

    ax.yaxis.set_major_formatter(FuncFormatter(dynamic_price_formatter))

    date_range_days = (
        dataframe["تاریخ میلادی"].max() - dataframe["تاریخ میلادی"].min()
    ).days

    if date_range_days <= 45:
        locator = mdates.WeekdayLocator(byweekday=mdates.SA, interval=1)
        date_format_str = "%m/%d"
    elif date_range_days <= 730:
        month_interval = 1 if date_range_days <= 365 else 3
        locator = mdates.MonthLocator(interval=month_interval)
        date_format_str = "%y/%m"
    else:
        locator = mdates.YearLocator()
        date_format_str = "%Y"

    def jalali_formatter(x, pos):
        try:
            jalali_date = jdatetime.date.fromgregorian(
                date=mdates.num2date(x).date())
            return persian_text(jalali_date.strftime(date_format_str))
        except:
            return ""

    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(FuncFormatter(jalali_formatter))

    # ========================================================================

    plt.setp(ax.get_xticklabels(), rotation=45,
             ha="right", fontproperties=font_prop)
    plt.setp(ax.get_yticklabels(), fontproperties=font_prop)

    ax.grid(True, which="major", linestyle="--", linewidth=0.5)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120)
    buf.seek(0)
    plt.close(fig)
    return buf


def handle_chart_request(features: dict):

    symbol = features["symbols"][0]
    start_date = features["date"]
    asset_type = features.get("type")

    df = None
    ylabel = "قیمت (تومان)"

    if asset_type == "currency":

        table_name = f"currency_{symbol}"
        dataframe = database_store.get_closest_row_as_df(
            table_name, features["date"])

        if not dataframe.empty:
            print(f"Fetching data for {features['symbols'][0]} from DB.")
            df = database_store.get_data_from_db(table_name)
        else:
            print(
                f"Fetching data for {features['symbols'][0]} from API and Saving to DB")
            full_history_df = currency.get_history_currency2(
                features["symbols"][0])
            database_store.save_data_to_db(full_history_df, table_name)
            df = database_store.get_data_from_db(table_name)

    elif asset_type == "gold":

        table_name = f"gold_{symbol}"
        dataframe = database_store.get_closest_row_as_df(
            table_name, features["date"])

        if not dataframe.empty:
            print(f"Fetching data for {features['symbols'][0]} from DB.")
            df = database_store.get_data_from_db(table_name)
        else:
            print(
                f"Fetching data for {features['symbols'][0]} from API and Saving to DB")
            full_history_df = gold.get_history_gold2(features["symbols"][0])
            database_store.save_data_to_db(full_history_df, table_name)
            df = database_store.get_data_from_db(table_name)

    elif asset_type == "cryptocurrency":

        table_name = f"cryptocurrency_{symbol}"
        dataframe = database_store.get_closest_row_as_df(
            table_name, features["date"])

        if not dataframe.empty:
            print(f"Fetching data for {features['symbols'][0]} from DB.")
            df = database_store.get_data_from_db(table_name)
        else:
            print(
                f"Fetching data for {features['symbols'][0]} from API and Saving to DB")
            full_history_df = cryptocurrency.get_history_cryptocurrency2(
                features["symbols"][0]
            )
            database_store.save_data_to_db(full_history_df, table_name)
            df = database_store.get_data_from_db(table_name)

        ylabel = "قیمت (دلار)"

    elif asset_type == "stock":

        sub_type = features.get("sub_type")

        if sub_type == "Iran Symbol":

            table_name = f"iran_symbol_{symbol}"

            dataframe = database_store.get_closest_row_as_df(
                table_name, features["date"])

            if not dataframe.empty:
                print(f"Fetching data for {features['symbols'][0]} from DB.")
                df = database_store.get_data_from_db(table_name)
            else:
                print(
                    f"Fetching data for {features['symbols'][0]} from API and Saving to DB"
                )
                full_history_df = iran_symbol.get_history_iran_symbol2(
                    features["symbols"][0]
                )
                database_store.save_data_to_db(full_history_df, table_name)
                df = database_store.get_data_from_db(table_name)

        elif sub_type == "Iran Index":

            table_name = f"iran_index_{symbol}"
            dataframe = database_store.get_closest_row_as_df(
                table_name, features["date"])

            if not dataframe.empty:
                print(f"Fetching data for {features['symbols'][0]} from DB.")
                df = database_store.get_data_from_db(table_name)
            else:
                print(
                    f"Fetching data for {features['symbols'][0]} from API and Saving to DB"
                )
                full_history_df = iran_index.get_history_iran_index2(
                    features["symbols"][0])
                database_store.save_data_to_db(full_history_df, table_name)
                df = database_store.get_data_from_db(table_name)

            ylabel = "مقدار شاخص"

        elif sub_type == "America Stock":

            table_name = f"america_stock_{symbol}"
            dataframe = database_store.get_closest_row_as_df(
                table_name, features["date"])

            if not dataframe.empty:
                print(f"Fetching data for {features['symbols'][0]} from DB.")
                df = database_store.get_data_from_db(table_name)
            else:
                print(
                    f"Fetching data for {features['symbols'][0]} from API and Saving to DB"
                )
                full_history_df = america_stock.get_history_america_stock2(
                    features["symbols"][0]
                )
                database_store.save_data_to_db(full_history_df, table_name)
                df = database_store.get_data_from_db(table_name)

            ylabel = "قیمت (دلار)"

        else:
            return "نمودار برای این نوع سهام هنوز پشتیبانی نمی‌شود."
    else:
        return "نوع دارایی برای رسم نمودار مشخص نیست."

    df["تاریخ میلادی"] = pd.to_datetime(df["تاریخ میلادی"])
    filtered_df = df[df["تاریخ میلادی"] >= pd.to_datetime(start_date)]

    if filtered_df.empty:
        return f"داده‌ای برای رسم نمودar {symbol} از این تاریخ به بعد وجود ندارد."

    title = f"نمودار {symbol}"

    try:
        chart_buffer = create_price_chart(
            dataframe=filtered_df, title=title, ylabel=ylabel
        )
        return chart_buffer
    except (ValueError, RuntimeError) as e:
        print(f"Error creating chart: {e}")
        return str(e)

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.ticker import FuncFormatter
import matplotlib.dates as mdates
import pandas as pd
import sqlite3
import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import quote
import jalali_pandas
import jdatetime
import io
import arabic_reshaper
from bidi.algorithm import get_display
from dateutil.relativedelta import relativedelta
import datetime
import currency
import gold
import cryptocurrency
import iran_symbol
import iran_index
import financial_core
from datetime import date
import america_stock

DB_NAME = "financial_data.db"


# --- DATABASE LOGIC ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_closest_row_as_df(
    table_name: str, target_date_str: str, threshold_days: int = 3
) -> pd.Series:
    """
    Checks if data for a specific date exists in the given table.
    بررسی می‌کند که آیا داده برای یک تاریخ مشخص در جدول مورد نظر وجود دارد یا خیر.
    """
    try:
        target_date = pd.to_datetime(target_date_str).date()

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            table_exists = cursor.fetchone()

            if table_exists is None:
                print(f"Table '{table_name}' does not exist.")
                return pd.Series(dtype=object)

            query = f"""
                SELECT * FROM "{table_name}"
                ORDER BY ABS(JULIANDAY(date("تاریخ میلادی")) - JULIANDAY(?))
                LIMIT 1
            """
            cursor.execute(query, (target_date.strftime("%Y-%m-%d"),))
            closest_date_result = cursor.fetchone()

            if closest_date_result is None:
                print(f"Table '{table_name}' is empty.")
                return pd.Series(dtype=object)

            closest_date = pd.to_datetime(closest_date_result[0]).date()
            closest_row_dict = dict(closest_date_result)
            date_difference = abs((target_date - closest_date).days)

            if date_difference <= threshold_days:
                print(
                    f"Found a close date ({closest_date}) within {threshold_days} days for {target_date_str} in '{table_name}'."
                )
                return pd.Series(closest_row_dict)
            else:
                print(
                    f"No close date found for {target_date_str} in '{table_name}'. Closest was {closest_date}."
                )
                return pd.Series(dtype=object)

    except Exception as e:
        print(
            f"An error occurred while checking for date {target_date_str} in table {table_name}: {e}"
        )
        return pd.Series(dtype=object)


def get_data_from_db(table_name: str) -> pd.DataFrame:
    """
    Fetches all data for a symbol from the database.
    If the data is outdated or the table is empty, it updates the data by
    fetching the full history from the relevant API and replacing the old table.
    """
    with get_db_connection() as conn:
        try:
            # Try to read existing data from the database
            df = pd.read_sql(f'SELECT * FROM "{table_name}"', conn)
            # Ensure the date column is in the correct format
            if not df.empty:
                df["تاریخ میلادی"] = pd.to_datetime(df["تاریخ میلادی"])
        except pd.io.sql.DatabaseError:
            # This exception occurs if the table does not exist
            df = pd.DataFrame()

    update_needed = False
    if df.empty:
        print(
            f"Table '{table_name}' is empty or does not exist. Fetching full history."
        )
        update_needed = True
    else:
        # Check if the most recent date in the DB is before today
        last_date_in_db = df["تاریخ میلادی"].max().date()
        today = date.today()
        if (today - last_date_in_db).days > 0:
            print(
                f"Data in '{table_name}' is outdated (last entry: {last_date_in_db}). Checking for updates."
            )
            update_needed = True

    if update_needed:
        print(f"Updating data for '{table_name}' from the source API...")
        try:
            full_history_df = None

            # Determine which function to call based on the table name prefix
            if table_name.startswith("currency_"):
                symbol = table_name.replace("currency_", "", 1)
                full_history_df = currency.get_history_currency2(symbol)
            elif table_name.startswith("gold_"):
                symbol = table_name.replace("gold_", "", 1)
                full_history_df = gold.get_history_gold2(symbol)
            elif table_name.startswith("cryptocurrency_"):
                symbol = table_name.replace("cryptocurrency_", "", 1)
                full_history_df = cryptocurrency.get_history_cryptocurrency2(symbol)
            elif table_name.startswith("iran_symbol_"):
                symbol = table_name.replace("iran_symbol_", "", 1)
                full_history_df = iran_symbol.get_history_iran_symbol2(symbol)
            elif table_name.startswith("iran_index_"):
                symbol = table_name.replace("iran_index_", "", 1)
                full_history_df = iran_index.get_history_iran_index2(symbol)
            elif table_name.startswith("america_stock_"):
                symbol = table_name.replace("america_stock_", "", 1)
                full_history_df = america_stock.get_history_america_stock2(symbol)

            if full_history_df is not None and not full_history_df.empty:
                # Save the new, updated data to the DB, replacing the old table
                save_data_to_db(full_history_df, table_name)
                print(f"Successfully updated '{table_name}' in the database.")
                # Return the newly fetched dataframe
                return full_history_df
            else:
                print(
                    f"Update failed for '{table_name}' (no data returned from API). Returning existing data."
                )
                return df  # Return old data if update fails

        except Exception as e:
            print(f"An error occurred during update for {table_name}: {e}")
            # In case of an error (e.g., API is down), return the old data to prevent crashing
            return df

    # If no update was needed, return the dataframe read from the DB
    print(f"Data for '{table_name}' is up-to-date. Returning from database.")
    return df


def save_data_to_db(df: pd.DataFrame, table_name: str):
    """Saves or appends a DataFrame to a specific table in the database."""
    with get_db_connection() as conn:
        # Use 'append' to add new data without deleting old data
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"Data for {table_name} saved to database.")

import streamlit as st
import re
import pandas as pd
import matplotlib.pyplot as plt
from bidi.algorithm import get_display
import matplotlib.font_manager as fm
import database_store
import currency
import gold
import cryptocurrency
import iran_index
import iran_symbol
import america_stock
import draw_chart
import gmini
import financial_core
import os 
import json

def format_return_results(returns_dict):
    cleaned_returns = {}
    for asset, value in returns_dict.items():
        try:
            cleaned_returns[asset] = float(value)
        except:
            cleaned_returns[asset] = 0.0

    lines = ["📊 **مقایسه بازدهی دارایی‌ها:**\n"]
    asset_line = []
    for asset, r in cleaned_returns.items():
        if r > 0:
            emoji = "🟢"
            formatted = f"{r:.2f}+%"
        elif r < 0:
            emoji = "🔴"
            formatted = f"{abs(r):.2f}-%"
        else:
            emoji = "⚪️"
            formatted = f"{r:.2f}%"
        asset_line.append(f"{emoji} {asset}: {formatted}")
    lines.append("  ".join(asset_line))

    lines.append("") 

    if cleaned_returns:
        max_asset = max(cleaned_returns, key=cleaned_returns.get)
        min_asset = min(cleaned_returns, key=cleaned_returns.get)
        max_val = cleaned_returns[max_asset]
        min_val = cleaned_returns[min_asset]
        max_formatted = f"{max_val:.2f}+%" if max_val >= 0 else f"{abs(max_val):.2f}-%"
        min_formatted = f"{min_val:.2f}+%" if min_val >= 0 else f"{abs(min_val):.2f}-%"
        
        max_emoji = "🟢" if max_val >= 0 else "🔴"
        min_emoji = "🟢" if min_val >= 0 else "🔴"
        
        lines.append(f"{max_emoji} 🔝 بیشترین بازده: {max_asset} {max_formatted}")
        lines.append(f"{min_emoji} 🔻 کمترین بازده: {min_asset} {min_formatted}")

    return "\n".join(lines)

def compare_assets(symbols, start_date):
    results = {}
    for symbol in symbols:
        table_name = ""
        if symbol in financial_core.currency_keywords:
                
                table_name = f"currency_{symbol}"
                df = database_store.get_closest_row_as_df(table_name, start_date) 
                if df.empty:
                    full_history = currency.get_history_currency2(symbol) 
                df = database_store.get_closest_row_as_df(table_name, start_date)
                percent_change = currency.get_currency_change(df, symbol, start_date)[1]
                results[symbol] = percent_change

                       
        elif symbol in financial_core.gold_keywords:
                
                keywords_path2 = os.path.join(os.path.dirname(__file__), "data", "golds.json")

                with open(keywords_path2, "r", encoding="utf-8") as f:
                    indexs = json.load(f)
                    
                mapping = indexs["mapping"]
                input_name = mapping.get(symbol, symbol)
                table_name = f"gold_{input_name}"
                print(table_name)

                df = database_store.get_closest_row_as_df(table_name, start_date)
                if df.empty:
                    full_history = gold.get_history_gold2(symbol)
                df = database_store.get_closest_row_as_df(table_name, start_date)
                percent_change = gold.get_gold_change(df, symbol, start_date)[1]
                results[symbol] = percent_change

        elif symbol in financial_core.cryptocurrency_keywords:
                
                table_name = f"cryptocurrency_{symbol}"
                df = database_store.get_closest_row_as_df(table_name, start_date)
                if df.empty:
                    full_history = cryptocurrency.get_history_cryptocurrency2(symbol)
                df = database_store.get_closest_row_as_df(table_name, start_date)
                percent_change = cryptocurrency.get_cryptocurrency_change(df, symbol, start_date)[1]
                results[symbol] = percent_change
                
        elif symbol in financial_core.index_symbols_keywords:
                table_name = f"iran_index_{symbol}"
                df = database_store.get_closest_row_as_df(table_name, start_date)
                if df.empty:
                    full_history = iran_index.get_history_iran_index2(symbol)
                df = database_store.get_closest_row_as_df(table_name, start_date)
                percent_change = iran_index.get_iran_index_change(df, symbol, start_date)[1]
                results[symbol] = percent_change

        elif symbol in financial_core.iran_symbols_keywords:
                table_name = f"iran_symbol_{symbol}"
                df = database_store.get_closest_row_as_df(table_name, start_date)
                if df.empty:
                    full_history = iran_symbol.get_history_iran_symbol2(symbol)
                df = database_store.get_closest_row_as_df(table_name, start_date)
                percent_change = iran_symbol.get_iran_symbol_change(df, symbol, start_date)[1]
                results[symbol] = percent_change

        elif symbol in financial_core.american_stock_symbols_keywords:
                table_name = f"america_stock_{symbol}"
                df = database_store.get_closest_row_as_df(table_name, start_date)
                if df.empty:
                    full_history = america_stock.get_history_america_stock2(symbol)
                df = database_store.get_closest_row_as_df(table_name, start_date)
                percent_change = america_stock.get_america_stock_change(df, symbol, start_date)[1]
                results[symbol] = percent_change

        else:
                continue

    return format_return_results(results)
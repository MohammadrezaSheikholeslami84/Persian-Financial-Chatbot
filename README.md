
# 📊 Persian Financial Chatbot  

An intelligent **Persian-language financial assistant** that lets you query live and historical data from multiple markets — including **currencies, gold, cryptocurrencies, Iranian stocks, and US stocks** — all by writing natural Persian sentences.  

This chatbot not only retrieves prices but can also calculate and compare asset returns over time, generate clear Persian-labeled charts, and optimize responses with a local **SQLite cache** for speed.  
It comes with both a **WebApp UI** and a **Telegram bot** for seamless user interaction.  


---

## 🚀 Features  

✅ **Real-time prices**  
Ask for the latest prices of assets:  
```text
قیمت سکه امامی امروز چنده؟  
قیمت بیت کوین الان چقدره؟
````


✅ **Historical prices**
Query past values:

```text
قیمت دلار هفته گذشته چند بود؟  
قیمت سهام فولاد دیروز چند بود؟
```

✅ **Price change & returns**
Check how much an asset has changed:

```text
قیمت یورو نسبت به ماه گذشته چقدر تغییر کرده؟  
بازدهی طلا در یک سال گذشته چقدر بوده؟
```

✅ **Chart generation**
Get professional **Persian-labeled charts**:

```text
نمودار قیمت بیت کوین در یک ماه گذشته رو نشون بده
```

✅ **Compare multiple assets**
Directly compare returns between assets:
```text
بازدهی بیت کوین و اتریوم در شش ماه گذشته رو مقایسه کن  
```

✅ **Smart caching**

* Speeds up repeated queries
* Stores results locally with **SQLite**

✅ **Multi-interface support**

* Telegram Bot: Chat directly with the financial assistant
* WebApp UI: Interactive web interface for queries, charts, and comparisons

---


## 📈 Supported Markets

* **Currencies**: دلار، یورو، پوند، درهم، دینار، فرانک، روبل
* **Gold & Coins**: انس جهانی، سکه امامی، بهار آزادی، نیم‌سکه، ربع سکه
* **Cryptocurrencies**: بیت‌کوین، اتریوم، کاردانو، ریپل، تتر
* **Iran Stocks**: نمادهای بورسی مثل خودرو، فملی، فولاد + شاخص کل، شاخص هم‌وزن، شاخص فرابورس
* **US Stocks**: اپل، گوگل، آمازون، تسلا، مایکروسافت

---

## 🛠 Tech Stack

* **Python**
* **Data Retrieval**: `requests`, `BeautifulSoup`
* **Data Handling**: `pandas`, `json`
* **Database**: `sqlite3` (local cache)
* **Visualization**: `matplotlib` (Persian-ready charts)
* **NLP & Parsing**: Regex-based feature extraction, custom Persian time parser

---

## ⚙️ How It Works

1. **User Input** → e.g. "قیمت دلار هفته گذشته چند بود؟"
2. **Feature Extraction** (`extract_features`)

   * Detects asset type & symbol
   * Parses Persian time (e.g., "هفته گذشته" → exact date)
   * Identifies request type (price, return, chart)
3. **Request Processing** → Chooses correct module
4. **Data Retrieval**

   * Checks cache (SQLite)
   * Falls back to APIs / scraping (`tgju.org`, `brsapi.ir`, `alphavantage.co`)
   * Updates cache
5. **Response Generation**

   * Text (prices, returns)
   * Chart (PNG with Persian labels)

---

## 📦 Installation

```bash
git clone https://github.com/MohammadrezaSheikholeslami84/Persian-Financial-Chatbot.git
cd Persian-Financial-Chatbot
pip install -r requirements.txt
```

---

## ▶️ Usage

```bash
python telegram_bot.py
```
or
```bash

python app.py
```

Then simply type queries in Persian like:

* `قیمت طلا امروز چنده؟`
* `نمودار بیت کوین در سه ماه گذشته`
* `قیمت سهام تسلا یک سال پیش`

---



## 📚 Roadmap

* [ ] Improve Persian NLP with BERT-based models
* [ ] Add more US and international stocks
* [ ] Expand to commodities (oil, silver, etc.)
* [ ] Web dashboard with Streamlit

---

## 🤝 Contributing

Contributions are welcome! Please open issues or submit PRs for bug fixes, improvements, or feature suggestions.

---

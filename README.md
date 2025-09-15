
# 📊 Persian Financial Chatbot  

An intelligent **Persian-language financial assistant** that allows users to query **live and historical data** across multiple markets — including **currencies, gold, cryptocurrencies, Iranian stocks, and US stocks** — using natural Persian sentences.  

👉 **Live Demo (Streamlit App):** [financial-llm.streamlit.app](https://financial-llm.streamlit.app/)  

This chatbot not only retrieves prices but can also calculate and compare asset returns over time, generate clear Persian-labeled charts, and optimize responses with a local **SQLite cache** for speed.  
It comes with both a **WebApp UI (Streamlit)** and a **Telegram bot** for seamless interaction.  

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
Generate professional **Persian-labeled charts**:

```text
نمودار قیمت بیت کوین در یک ماه گذشته رو نشون بده
```

✅ **Compare multiple assets**
Directly compare returns:

```text
بازدهی بیت کوین و اتریوم در شش ماه گذشته رو مقایسه کن
```

✅ **Smart caching**

* Speeds up repeated queries
* Stores results locally with **SQLite**

✅ **Multi-interface support**

* **Streamlit WebApp:** [financial-llm.streamlit.app](https://financial-llm.streamlit.app/)
* **Telegram Bot:** Chat directly with the financial assistant

---

## 📈 Supported Markets

* **Currencies:** USD, EUR, GBP, AED, Dinar, CHF, RUB
* **Gold & Coins:** Global ounce, Emami coin, Bahar Azadi, half & quarter coins
* **Cryptocurrencies:** Bitcoin, Ethereum, Cardano, Ripple, Tether
* **Iran Stocks:** Symbols like خودرو, فملی, فولاد + indices (TEDPIX, equal-weight, IFB)
* **US Stocks:** Apple, Google, Amazon, Tesla, Microsoft

---

## 🛠 Tech Stack

* **Python**
* **Data Retrieval:** `requests`, `BeautifulSoup`
* **Data Handling:** `pandas`, `json`
* **Database:** `sqlite3` (local cache)
* **Visualization:** `matplotlib` (Persian-ready charts)
* **NLP & Parsing:** Regex-based feature extraction, custom Persian time parser
* **Deployment:** Streamlit WebApp + Telegram Bot

---

## ⚙️ How It Works

1. **User Input** → Example: *"قیمت دلار هفته گذشته چند بود؟"*
2. **Feature Extraction** (`extract_features`)

   * Detects asset type & symbol
   * Parses Persian time (e.g., "هفته گذشته" → exact date)
   * Identifies request type (price, return, chart)
3. **Request Processing** → Chooses correct module
4. **Data Retrieval**

   * Checks **SQLite cache**
   * Falls back to APIs / scraping (`tgju.org`, `brsapi.ir`, `alphavantage.co`)
   * Updates cache
5. **Response Generation**

   * Text response (price, return, comparison)
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

### Run Telegram Bot

```bash
python telegram_bot.py
```

### Run Streamlit App

```bash
streamlit run app.py
```

Then type queries in Persian like:

* `قیمت طلا امروز چنده؟`
* `نمودار بیت کوین در سه ماه گذشته`
* `قیمت سهام تسلا یک سال پیش`

Or try it directly online 👉 [financial-llm.streamlit.app](https://financial-llm.streamlit.app/)

---

## 📚 Roadmap

* [ ] Improve Persian NLP with BERT-based models
* [ ] Add more US and international stocks
* [ ] Expand to commodities (oil, silver, etc.)
* [ ] Enhance web dashboard with Streamlit

---

## 🤝 Contributing

Contributions are welcome! Please open issues or submit PRs for bug fixes, improvements, or new features.

---


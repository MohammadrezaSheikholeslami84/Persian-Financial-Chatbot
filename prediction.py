import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt
import os
import datetime
import joblib

# ----- آماده‌سازی داده روی pct_change -----
def prepare_data_pct_tf(df, window_size=60, val_ratio=0.2, test_ratio=0.1):
    df = df.copy()
    df["pct_change"] = df["پایانی"].pct_change()
    df = df.dropna().reset_index(drop=True)

    values = df["pct_change"].values.reshape(-1,1)
    scaler = MinMaxScaler()
    values_scaled = scaler.fit_transform(values)

    X, y = [], []
    for i in range(len(values_scaled) - window_size):
        X.append(values_scaled[i:i+window_size])
        y.append(values_scaled[i+window_size])
    X, y = np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

    total_size = len(X)
    test_size = int(total_size * test_ratio)
    val_size = int(total_size * val_ratio)
    train_size = total_size - val_size - test_size

    X_train, y_train = X[:train_size], y[:train_size]
    X_val, y_val = X[train_size:train_size+val_size], y[train_size:train_size+val_size]
    X_test, y_test = X[train_size+val_size:], y[train_size+val_size:]

    return X_train, y_train, X_val, y_val, X_test, y_test, scaler

# ----- ساخت مدل LSTM -----
def build_lstm_model(input_shape, hidden_size=64, num_layers=2):
    model = Sequential()
    for i in range(num_layers):
        return_sequences = i < num_layers - 1
        if i == 0:
            model.add(LSTM(hidden_size, return_sequences=return_sequences, input_shape=input_shape))
        else:
            model.add(LSTM(hidden_size, return_sequences=return_sequences))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mse')
    return model

# ----- آموزش مدل -----
def train_model_tf(model, X_train, y_train, X_val, y_val, epochs=50, batch_size=32):
    es = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
    history = model.fit(X_train, y_train, validation_data=(X_val, y_val),
                        epochs=epochs, batch_size=batch_size, callbacks=[es], verbose=2)
    return history

# ----- ذخیره مدل و scaler (نسخه امن با فرمت جدید Keras) -----
def save_model_tf(model, scaler, model_path="lstm_pct_tf.keras", scaler_path="scaler_pct_tf.pkl"):
    """
    مدل و scaler را ذخیره می‌کند.
    model_path: مسیر ذخیره مدل (فرمت .keras)
    scaler_path: مسیر ذخیره scaler (joblib)
    """
    # ذخیره مدل با فرمت جدید Keras
    model.save(model_path)
    # ذخیره scaler
    joblib.dump(scaler, scaler_path)
    print(f"Model saved to {model_path}")
    print(f"Scaler saved to {scaler_path}")

# ----- بارگذاری مدل و scaler -----
def load_model_tf(model_path="lstm_pct_tf.keras", scaler_path="scaler_pct_tf.pkl"):
    """
    مدل و scaler ذخیره شده را بارگذاری می‌کند.
    """
    # بارگذاری مدل از فرمت جدید Keras
    model = tf.keras.models.load_model(model_path)
    # بارگذاری scaler
    scaler = joblib.load(scaler_path)
    print(f"Model loaded from {model_path}")
    print(f"Scaler loaded from {scaler_path}")
    return model, scaler

# ----- پیش‌بینی فردا روی pct_change -----
def predict_tomorrow_pct_tf(model, df, scaler, window_size=60):
    df = df.copy()
    df["pct_change"] = df["پایانی"].pct_change()
    df = df.dropna().reset_index(drop=True)
    last_window = df["pct_change"].values[-window_size:].reshape(-1,1)
    last_window_scaled = scaler.transform(last_window)

    X = last_window_scaled.reshape(1, window_size, 1)
    pred_scaled = model.predict(X, verbose=0)
    pred_pct = scaler.inverse_transform(pred_scaled)

    last_price = df["پایانی"].iloc[-1]
    pred_price = last_price * (1 + pred_pct[0][0])
    return pred_price

# ----- پیش‌بینی n روز آینده روی pct_change -----
def predict_future_pct_tf(model, df, scaler, window_size=60, n_days=5):
    df = df.copy()
    df["pct_change"] = df["پایانی"].pct_change()
    df = df.dropna().reset_index(drop=True)
    last_window = df["pct_change"].values[-window_size:].reshape(-1,1)
    last_window_scaled = scaler.transform(last_window)
    last_window_scaled = last_window_scaled.reshape(1, window_size, 1)

    preds = []
    for _ in range(n_days):
        pred_scaled = model.predict(last_window_scaled, verbose=0)
        preds.append(pred_scaled[0][0])
        # اضافه کردن پیش‌بینی به آخرین پنجره و حذف اولین عنصر
        last_window_scaled = np.append(last_window_scaled[:,1:,:], pred_scaled.reshape(1,1,1), axis=1)

    preds = scaler.inverse_transform(np.array(preds).reshape(-1,1))
    last_price = df["پایانی"].iloc[-1]
    price_preds = [last_price * (1 + p[0]) for p in preds]
    return price_preds

# ----- ارزیابی مدل -----
def evaluate_model_pct_tf(model, X, y, scaler):
    preds = model.predict(X, verbose=0)
    preds_inv = scaler.inverse_transform(preds)
    y_inv = scaler.inverse_transform(y.reshape(-1,1))

    trend_true = np.sign(y_inv)
    trend_pred = np.sign(preds_inv)
    accuracy = np.mean(trend_true == trend_pred) * 100
    print(f"Trend Accuracy: {accuracy:.2f}%")


    mae = mean_absolute_error(y_inv, preds_inv)
    rmse = np.sqrt(mean_squared_error(y_inv, preds_inv))
    return mae, rmse, y_inv, preds_inv



# ----- پاسخ به کاربر -----
def answer_user_question_pct_tf(question, model, df, scaler):
    import re
    if "فردا" in question:
        price = predict_tomorrow_pct_tf(model, df, scaler)
        return f"📊 پیش‌بینی مدل: قیمت پایانی فردا حدود {price:.2f} خواهد بود."
    elif "روز" in question:
        match = re.search(r"(\d+)\s*روز", question)
        if match:
            n = int(match.group(1))
            preds = predict_future_pct_tf(model, df, scaler, n_days=n)
            return f"📊 پیش‌بینی {n} روز آینده:\n" + "\n".join(
                [f"روز {i+1}: {p:.2f}" for i,p in enumerate(preds)]
            )
    return "فعلاً فقط می‌توانم قیمت فردا یا چند روز آینده را پیش‌بینی کنم."

# ----- تولید نمودار پیش‌بینی -----
def save_prediction_chart_pct_tf(true_train, pred_train,
                                 true_val, pred_val,
                                 true_test, pred_test,
                                 last_price,
                                 tomorrow_price=None,
                                 folder_path="static/charts"):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # بازسازی قیمت‌ها از pct_change
    def pct_to_price(last_price, pct_array):
        prices = []
        price = last_price
        for p in pct_array:
            price = price * (1 + p)
            prices.append(price)
        return prices

    price_train_true = pct_to_price(last_price, true_train)
    price_train_pred = pct_to_price(last_price, pred_train)
    price_val_true = pct_to_price(price_train_true[-1], true_val)
    price_val_pred = pct_to_price(price_train_pred[-1], pred_val)
    price_test_true = pct_to_price(price_val_true[-1], true_test)
    price_test_pred = pct_to_price(price_val_pred[-1], pred_test)

    plt.figure(figsize=(12,6))
    # Train
    plt.plot(price_train_pred, label="Train Predicted", color="blue")
    plt.plot(price_train_true, label="Train True", color="cyan")
    # Validation
    offset_val = len(price_train_pred)
    plt.plot(range(offset_val, offset_val+len(price_val_pred)), price_val_pred, label="Validation Predicted", color="orange")
    plt.plot(range(offset_val, offset_val+len(price_val_true)), price_val_true, label="Validation True", color="yellow")
    # Test
    offset_test = offset_val + len(price_val_pred)
    plt.plot(range(offset_test, offset_test+len(price_test_pred)), price_test_pred, label="Test Predicted", color="red")
    plt.plot(range(offset_test, offset_test+len(price_test_true)), price_test_true, label="Test True", color="pink")
    # Prediction for tomorrow
    if tomorrow_price is not None:
        plt.scatter(offset_test+len(price_test_pred)+1, tomorrow_price, color="green", s=100, label="Tomorrow Prediction")

    plt.legend()
    plt.title("مقایسه پیش‌بینی مدل و داده واقعی (بر اساس pct_change)")
    plt.xlabel("Index")
    plt.ylabel("قیمت دلار")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chart_{timestamp}.png"
    filepath = os.path.join(folder_path, filename)

    plt.savefig(filepath, bbox_inches='tight')
    plt.close()
    return filepath

# ----- پیش‌بینی و آموزش یک‌بار برای LLM -----
def predict(df, user_input, number_years=4, window_size=60, epochs=30):
    df = df.copy()
    df["تاریخ میلادی"] = pd.to_datetime(df["تاریخ میلادی"])
    df = df.sort_values("تاریخ میلادی")
    end_date = df["تاریخ میلادی"].max()
    start_date = end_date - pd.DateOffset(years=number_years)
    df_last = df[df["تاریخ میلادی"] >= start_date].copy()

    # آماده‌سازی داده
    X_train, y_train, X_val, y_val, X_test, y_test, scaler = prepare_data_pct_tf(df_last, window_size=window_size)

    # مدل
    model = build_lstm_model(input_shape=(window_size,1))
    train_model_tf(model, X_train, y_train, X_val, y_val, epochs=epochs)

    # ذخیره مدل و scaler
    save_model_tf(model, scaler)

    # بارگذاری دوباره مدل
    model, scaler = load_model_tf()

    # ارزیابی روی داده‌ها
    results = {}
    for name, X, y in zip(["Train","Validation","Test"], [X_train,X_val,X_test], [y_train,y_val,y_test]):
        mae, rmse, true, preds = evaluate_model_pct_tf(model, X, y, scaler)
        print(f"{name} - MAE: {mae:.4f}, RMSE: {rmse:.4f}")
        results[name] = {"true": true.flatten(), "pred": preds.flatten()}

    # پیش‌بینی فردا
    tomorrow_price = predict_tomorrow_pct_tf(model, df_last, scaler, window_size=window_size)
    last_price = df_last["پایانی"].iloc[-1]

    # تولید و ذخیره نمودار
    chart_path = save_prediction_chart_pct_tf(
        true_train=results["Train"]["true"], pred_train=results["Train"]["pred"],
        true_val=results["Validation"]["true"], pred_val=results["Validation"]["pred"],
        true_test=results["Test"]["true"], pred_test=results["Test"]["pred"],
        last_price=last_price,
        tomorrow_price=tomorrow_price,
        folder_path="static/charts"
    )

    # پاسخ به کاربر
    response_text = answer_user_question_pct_tf(user_input, model, df_last, scaler)
    print(response_text)

    return {"text": response_text, "chart_path": chart_path}
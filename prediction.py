import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import matplotlib.pyplot as plt
import os
import datetime
import io

# ----- تنظیمات -----
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ----- مدل LSTM -----
class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, output_size=1):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

# ----- آماده‌سازی داده روی pct_change -----
def prepare_data_pct(df, window_size=60, val_ratio=0.2, test_ratio=0.1):
    df["pct_change"] = df["پایانی"].pct_change()
    df = df.dropna().reset_index(drop=True)

    values = df["pct_change"].values.reshape(-1, 1)
    scaler = MinMaxScaler()
    values_scaled = scaler.fit_transform(values)

    X, y = [], []
    for i in range(len(values_scaled) - window_size):
        X.append(values_scaled[i:i + window_size])
        y.append(values_scaled[i + window_size])
    X, y = np.array(X), np.array(y)

    total_size = len(X)
    test_size = int(total_size * test_ratio)
    val_size = int(total_size * val_ratio)
    train_size = total_size - val_size - test_size

    X_train, y_train = X[:train_size], y[:train_size]
    X_val, y_val = X[train_size:train_size+val_size], y[train_size:train_size+val_size]
    X_test, y_test = X[train_size+val_size:], y[train_size+val_size:]

    return X_train, y_train, X_val, y_val, X_test, y_test, scaler

# ----- آموزش مدل -----
def train_model(model, train_loader, val_loader, epochs=50, lr=0.001):
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        model.train()
        batch_losses = []
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            output = model(X_batch)
            loss = criterion(output, y_batch)
            loss.backward()
            optimizer.step()
            batch_losses.append(loss.item())

        train_loss = np.mean(batch_losses)

        model.eval()
        val_losses = []
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                output = model(X_batch)
                loss = criterion(output, y_batch)
                val_losses.append(loss.item())
        val_loss = np.mean(val_losses)
        print(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")

# ----- ذخیره و بارگذاری مدل -----
def save_model(model, scaler, model_path="lstm_pct_model.pth", scaler_path="scaler_pct.pkl"):
    torch.save(model.state_dict(), model_path)
    joblib.dump(scaler, scaler_path)

def load_model(model_path="lstm_pct_model.pth", scaler_path="scaler_pct.pkl"):
    model = LSTMModel().to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    scaler = joblib.load(scaler_path)
    return model, scaler

# ----- پیش‌بینی فردا روی pct_change -----
def predict_tomorrow_pct(model, df, scaler, window_size=60):
    df = df.copy()
    df["pct_change"] = df["پایانی"].pct_change()
    df = df.dropna().reset_index(drop=True)
    last_window = df["pct_change"].values[-window_size:].reshape(-1,1)
    last_window_scaled = scaler.transform(last_window)

    X = torch.tensor(last_window_scaled, dtype=torch.float32).unsqueeze(0).to(device)
    with torch.no_grad():
        pred_scaled = model(X).cpu().numpy()
    pred_pct = scaler.inverse_transform(pred_scaled)

    last_price = df["پایانی"].iloc[-1]
    pred_price = last_price * (1 + pred_pct[0][0])
    return pred_price

# ----- پیش‌بینی n روز آینده روی pct_change -----
def predict_future_pct(model, df, scaler, window_size=60, n_days=5):
    df = df.copy()
    df["pct_change"] = df["پایانی"].pct_change()
    df = df.dropna().reset_index(drop=True)
    last_window = df["pct_change"].values[-window_size:].reshape(-1,1)
    last_window_scaled = scaler.transform(last_window)
    last_window_scaled = last_window_scaled.reshape(1, window_size, 1)

    preds = []
    with torch.no_grad():
        for _ in range(n_days):
            X = torch.tensor(last_window_scaled, dtype=torch.float32).to(device)
            pred_scaled = model(X).cpu().numpy()
            preds.append(pred_scaled[0][0])
            last_window_scaled = np.append(last_window_scaled[:,1:,:], [[pred_scaled]], axis=1)

    preds = scaler.inverse_transform(np.array(preds).reshape(-1,1))
    last_price = df["پایانی"].iloc[-1]
    price_preds = [last_price * (1 + p[0]) for p in preds]
    return price_preds

# ----- پاسخ به کاربر -----
def answer_user_question_pct(question, model, df, scaler):
    if "فردا" in question:
        price = predict_tomorrow_pct(model, df, scaler)
        return f"📊 پیش‌بینی مدل: قیمت پایانی فردا حدود {price:.2f} خواهد بود."
    elif "روز" in question:
        import re
        match = re.search(r"(\d+)\s*روز", question)
        if match:
            n = int(match.group(1))
            preds = predict_future_pct(model, df, scaler, n_days=n)
            return f"📊 پیش‌بینی {n} روز آینده:\n" + "\n".join(
                [f"روز {i+1}: {p:.2f}" for i,p in enumerate(preds)]
            )
    return "فعلاً فقط می‌توانم قیمت فردا یا چند روز آینده را پیش‌بینی کنم."

# ----- ارزیابی مدل -----
def evaluate_model_pct(model, X, y, scaler):
    model.eval()
    with torch.no_grad():
        X = torch.tensor(X, dtype=torch.float32).to(device)
        y = torch.tensor(y, dtype=torch.float32).to(device)
        preds = model(X).cpu().numpy()
        true = y.cpu().numpy()
    preds = scaler.inverse_transform(preds)
    true = scaler.inverse_transform(true)
    mae = mean_absolute_error(true, preds)
    rmse = np.sqrt(mean_squared_error(true, preds))
    return mae, rmse, true, preds

# ----- پیش‌بینی و آموزش یک‌بار برای LLM -----
def predict(df, user_input, number_years=4, window_size=60, epochs=30):
    df = df.copy()
    df["تاریخ میلادی"] = pd.to_datetime(df["تاریخ میلادی"])
    df = df.sort_values("تاریخ میلادی")
    end_date = df["تاریخ میلادی"].max()
    start_date = end_date - pd.DateOffset(years=number_years)
    df_last = df[df["تاریخ میلادی"] >= start_date].copy()

    # آماده‌سازی داده
    X_train, y_train, X_val, y_val, X_test, y_test, scaler = prepare_data_pct(df_last, window_size=window_size)
    train_loader = DataLoader(TensorDataset(torch.tensor(X_train, dtype=torch.float32),
                                            torch.tensor(y_train, dtype=torch.float32)), batch_size=32, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.tensor(X_val, dtype=torch.float32),
                                          torch.tensor(y_val, dtype=torch.float32)), batch_size=32, shuffle=False)

    # مدل
    model = LSTMModel().to(device)
    train_model(model, train_loader, val_loader, epochs=epochs)

    # ذخیره مدل و scaler
    save_model(model, scaler)

    # بارگذاری دوباره مدل
    model, scaler = load_model()

    # ارزیابی روی داده‌ها
    results = {}
    for name, X, y in zip(["Train", "Validation", "Test"], [X_train, X_val, X_test], [y_train, y_val, y_test]):
        mae, rmse, true, preds = evaluate_model_pct(model, X, y, scaler)
        print(f"{name} - MAE: {mae:.4f}, RMSE: {rmse:.4f}")
        results[name] = {"true": true, "pred": preds}

    # پیش‌بینی فردا برای نمودار
    tomorrow_price = predict_tomorrow_pct(model, df_last, scaler, window_size=window_size)
    last_price = df_last["پایانی"].iloc[-1]

    # تولید و ذخیره نمودار
    chart_path = save_prediction_chart_pct(
        true_train=results["Train"]["true"], pred_train=results["Train"]["pred"],
        true_val=results["Validation"]["true"], pred_val=results["Validation"]["pred"],
        true_test=results["Test"]["true"], pred_test=results["Test"]["pred"],
        last_price=last_price,
        tomorrow_price=tomorrow_price,
        folder_path="static/charts"
    )

    # پاسخ به کاربر
    response_text = answer_user_question_pct(user_input, model, df_last, scaler)

    return {"text": response_text, "chart_path": chart_path}


def save_prediction_chart_pct(true_train, pred_train,
                              true_val, pred_val,
                              true_test, pred_test,
                              last_price,
                              tomorrow_price=None,
                              folder_path="static/charts"):
    """
    تولید نمودار مقایسه قیمت واقعی و پیش‌بینی شده بر اساس pct_change
    و ذخیره به فولدر مشخص
    """
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

    # بازسازی قیمت واقعی و پیش‌بینی شده
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
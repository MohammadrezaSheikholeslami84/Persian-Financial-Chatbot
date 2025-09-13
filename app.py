# app.py
from flask import Flask, render_template, request, jsonify, url_for
import os
import datetime
import io
from pydub import AudioSegment
import financial_core as func

# --- HuggingFace Whisper Setup ---
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import torch
import torchaudio
import gmini
'''
print("Loading HuggingFace Whisper model (large-fa)...")
device = "cuda" if torch.cuda.is_available() else "cpu"
hf_whisper_processor = WhisperProcessor.from_pretrained("vhdm/whisper-large-fa-v1")
hf_whisper_model = WhisperForConditionalGeneration.from_pretrained("vhdm/whisper-large-fa-v1").to(device)
print(f"Model loaded on {device}.")
'''

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")


@app.route("/")
def home():
    """Renders the main chat page."""
    charts_dir = os.path.join(app.static_folder, "charts")
    if not os.path.exists(charts_dir):
        os.makedirs(charts_dir)

    audio_dir = os.path.join(app.static_folder, "audio")
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)

    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    """Receives audio data, converts it to WAV, and transcribes it using HF Whisper."""
    if "audio_data" not in request.files:
        return jsonify({"error": "فایل صوتی در درخواست یافت نشد."}), 400

    audio_file = request.files["audio_data"]

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_webm_path = os.path.join(app.static_folder, "audio", f"temp_audio_{timestamp}.webm")
    temp_wav_path = os.path.join(app.static_folder, "audio", f"temp_audio_{timestamp}.wav")

    try:
        # ذخیره موقت WebM
        audio_file.save(temp_webm_path)

        # تبدیل WebM به WAV
        audio = AudioSegment.from_file(temp_webm_path)
        audio.export(temp_wav_path, format="wav")

        # بارگذاری WAV با torchaudio
        waveform, sr = torchaudio.load(temp_wav_path)
        if sr != 16000:
            waveform = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)(waveform)

        # پردازش صوت
        input_features = hf_whisper_processor(
            waveform.squeeze().numpy(), sampling_rate=16000, return_tensors="pt"
        ).input_features.to(device)

        # تولید متن
        predicted_ids = hf_whisper_model.generate(input_features)
        transcribed_text = hf_whisper_processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )[0]

        return jsonify({"transcribed_text": transcribed_text})

    except Exception as e:
        print(f"Error during transcription: {e}")
        return jsonify({"error": "خطا در پردازش فایل صوتی."}), 500

    finally:
        # پاک کردن فایل‌های موقت
        if os.path.exists(temp_webm_path):
            os.remove(temp_webm_path)
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)


@app.route("/chat", methods=["POST"])
def chat():
    """Handles the text chat request from the user."""
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    bot_response_data = func.process_request(user_message)
    response_type = bot_response_data.get("type")
    output_text = gmini.rag_response(user_message,bot_response_data.get("text"))
    print(output_text)

    if response_type == "text":
        return jsonify({
            "type": "text",
            "content": output_text,
        })

    elif response_type == "image":
        try:
            chart_buffer = bot_response_data.get("image")
            caption = bot_response_data.get("caption", "نمودار")

            if not isinstance(chart_buffer, io.BytesIO):
                return jsonify({
                    "type": "text",
                    "content": "خطا: خروجی نمودار از نوع معتبر (BytesIO) نیست.",
                })

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chart_{timestamp}.png"
            filepath = os.path.join(app.static_folder, "charts", filename)

            with open(filepath, "wb") as f:
                f.write(chart_buffer.getbuffer())

            chart_url = url_for("static", filename=f"charts/{filename}")

            return jsonify({"type": "image", "url": chart_url, "alt_text": caption})
        except Exception as e:
            print(f"Error processing chart in app.py: {e}")
            return jsonify({"type": "text", "content": f"خطا در ساخت و ذخیره نمودار: {e}"})

    else:
        return jsonify({"type": "text", "content": "نوع پاسخ از سرور ناشناخته است."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

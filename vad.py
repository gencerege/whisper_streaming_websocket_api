from flask import Flask, render_template
from flask_sock import Sock
import numpy as np
import wave

app = Flask(__name__)

sock = Sock(app)

@app.route("/")
def home():
    return render_template("vad.html")

@sock.route("/save")
def save_audio(ws):
    all_speech = np.array([], dtype=np.float32)
    while True: 
        data = ws.receive() 
        if data == "STOP":
            all_speech_int = (all_speech * 32767).astype(np.int16)
            audio_file = wave.open("output.wav", "wb")
            audio_file.setnchannels(1)
            audio_file.setsampwidth(2)
            audio_file.setframerate(16000)
            audio_file.writeframes(b''.join(all_speech_int))
            audio_file.close()
            all_speech = np.array([], dtype=np.float32)

        else: 
            audio = np.frombuffer(data, dtype=np.float32)
            print(len(audio))
            all_speech = np.append(all_speech, audio)
            print("SA")



if __name__ == "__main__":
    app.run(port=5004)
from flask import Flask, render_template
from flask_sock import Sock
from whisper_streaming.whisper_online import *
from live_transcriber_ws import LiveTranscriberWS

app = Flask(__name__)    

model = MLXWhisper(lan = 'tr', model_dir="../models/whisper-v3-turbo-mlx")
online = OnlineASRProcessor(model)

sock = Sock(app)
sockets = []
@app.route("/")
def home():    
    return render_template("vad.html")

@sock.route("/save")
def save_audio(ws):
    transcriber = LiveTranscriberWS(ws)
    transcriber.transcribe(online)


if __name__ == "__main__":
    app.run(port=5004)
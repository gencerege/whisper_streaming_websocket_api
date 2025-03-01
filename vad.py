from flask import Flask, render_template
from flask_sock import Sock
from whisper_streaming.whisper_online import *
from live_transcriber_ws import LiveTranscriberWS
import threading

app = Flask(__name__)    

model = MLXWhisper(lan = 'tr', model_dir="../models/whisper-v3-turbo-mlx")
online = OnlineASRProcessor(model)

sock = Sock(app)
sockets = []

transcriber = LiveTranscriberWS(online)

@app.route("/")
def home():
    print(threading.enumerate())
    return render_template("vad.html")

@sock.route("/save")
def save_audio(ws):
    transcriber.setup(ws)
    transcriber.transcriber_thread.join() # Default Use, transcript is sent to client.

    # while True: # or you can remove the above line and use your own loop to access and process transcript. 
    #     time.sleep(5)
    #     print(f"{transcriber.commited[2]}{transcriber.rest[2]}")
        
 


    print("Websocket Closed")



if __name__ == "__main__":
    app.run()
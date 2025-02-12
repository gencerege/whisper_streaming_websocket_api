from flask import Flask, render_template
from flask_sock import Sock
import numpy as np
import wave
import threading
from whisper_streaming.whisper_online import *

app = Flask(__name__)



def receive_audio(ws):
    global recording_on
    recording_on = True
    while True: 
        global all_speech
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
            ws.send("Recorded Segment Saved")
            recording_on = False

        else: 
            recording_on = True
            # ws.send("Voice Received\n")
            audio = np.frombuffer(data, dtype=np.float32)
            # print(len(audio))
            all_speech = np.append(all_speech, audio)
            # print("SA")



sock = Sock(app)
sockets = []
@app.route("/")
def home():
    return render_template("vad.html")


all_speech = np.array([], dtype=np.float32)
recording_on = False
model = MLXWhisper(lan = 'tr', model_dir="../whisper-v3-turbo")
online = OnlineASRProcessor(model)
@sock.route("/save")
def save_audio(ws):
    receiver_thread = threading.Thread(target = receive_audio, args = [ws])
    receiver_thread.start()
    previous_length = 0
    while True:
        if recording_on:
            length_of_new_frame = len(all_speech) - previous_length
            chunk_length = 15872
            if length_of_new_frame >= 15872:
                # ws.send(f"Full frame: {len(all_speech[previous_length: previous_length + length_of_new_frame])}")
                # ws.send(f"Samples sent: audio[{previous_length}:{previous_length+length_of_new_frame}]")
                online.insert_audio_chunk(all_speech[previous_length:previous_length + chunk_length])
                commited, rest = online.process_iter()
                ws.send(f"{commited[2]} {rest[2]}")
                previous_length += chunk_length

            elif 15872 > length_of_new_frame > 0:
                # ws.send(f"End frame: {length_of_new_frame}")
                # ws.send(f"Samples sent: audio[{previous_length}:{previous_length+length_of_new_frame}]")
                online.insert_audio_chunk(all_speech[previous_length:previous_length + length_of_new_frame])
                commited, rest = online.process_iter()
                ws.send(f"{commited[2]} {rest[2]}")
                previous_length += length_of_new_frame

            else:
                pass
        else:
            previous_length = 0    




if __name__ == "__main__":
    app.run(port=5004)
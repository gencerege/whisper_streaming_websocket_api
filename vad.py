from flask import Flask, render_template
from flask_sock import Sock
import numpy as np
import wave
import threading
from whisper_streaming.whisper_online import *

app = Flask(__name__)


def receive_audio(ws):
    global recording_on
    recording_on = "ON"
    try:
        while True: 
            global all_speech
            data = ws.receive() 
            if data == "Pause" or data == "Stop":
                all_speech_int = (all_speech * 32767).astype(np.int16)
                audio_file = wave.open("output.wav", "wb")
                audio_file.setnchannels(1)
                audio_file.setsampwidth(2)
                audio_file.setframerate(16000)
                audio_file.writeframes(b''.join(all_speech_int))
                audio_file.close()
                if data == "Pause":
                    recording_on = "PAUSED"
                else:
                    recording_on = "STOPPED"
            else:   
                print("aaa")
                recording_on = "ON"
                # ws.send("Voice Received\n")
                audio = np.frombuffer(data, dtype=np.float32)
                # print(len(audio))
                all_speech = np.append(all_speech, audio)
                # print("SA")
    except Exception as es:
        recording_on = "INTERRUPTED"
        return print(es)

# TODO: Make stop button work even if the connection was interrupted.
    # Stop button don't work after interruption because we do not have a websocket anymore. 
    # If we can reinitialize connection without pressing start only on interrupts then we can make the stop button work. 
    # In case of interrupts we can have reconnecting status text displayed
    # and Enable stop button once reconnected. 

sock = Sock(app)
sockets = []
@app.route("/")
def home():
    print(threading.enumerate())
    return render_template("vad.html")


all_speech = np.array([], dtype=np.float32)
recording_on = "OFF"
model = MLXWhisper(lan = 'tr', model_dir="../whisper-v3-turbo")
online = OnlineASRProcessor(model)
previous_length = 0
@sock.route("/save")
def save_audio(ws):
    global previous_length
    global all_speech
    receiver_thread = threading.Thread(target = receive_audio, args = [ws]).start()
    print(recording_on)
    print(threading.enumerate())
    while recording_on == "ON" or recording_on == "PAUSED" or previous_length < len(all_speech):
        if previous_length < len(all_speech):
            length_of_new_frame = len(all_speech) - previous_length
            chunk_length = 16384 # TODO: Set Chunk Length from server?
            if length_of_new_frame >= chunk_length:
                # ws.send(f"Full frame: {len(all_speech[previous_length: previous_length + length_of_new_frame])}")
                # ws.send(f"Samples sent: audio[{previous_length}:{previous_length+length_of_new_frame}]")
                online.insert_audio_chunk(all_speech[previous_length:previous_length + chunk_length])
                commited, rest = online.process_iter()
                try:
                    ws.send(f"{commited[2]} {rest[2]}")
                except:
                    print("Could not send last block. Will send once the connection is reopened")    
                previous_length += chunk_length

            elif chunk_length > length_of_new_frame > 0:
                # ws.send(f"End frame: {length_of_new_frame}")
                # ws.send(f"Samples sent: audio[{previous_length}:{previous_length+length_of_new_frame}]")
                online.insert_audio_chunk(all_speech[previous_length:previous_length + length_of_new_frame])
                if length_of_new_frame > 8 * 512:
                    commited, rest = online.process_iter()
                    try:
                        ws.send(f"{commited[2]} {rest[2]}")
                    except:
                        print("Could not send last block. Will send once the connection is reopened")  
                previous_length += length_of_new_frame
            else:
                pass 

    if recording_on == "STOPPED":
        online.init()
        all_speech = np.array([], dtype=np.float32) ## HOW DOES ADDING THIS LINE CAN PREVENT MY CONNECTION TO THE WEBSOCKET? The answer was that python was throwing an UNBOUNDLOCALERROR
        previous_length = 0

    return print("Websocket thread closed")

            




if __name__ == "__main__":
    app.run(port=5004)
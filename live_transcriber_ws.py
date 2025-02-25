import numpy as np
import wave
import threading


class LiveTranscriberWS():
    def __init__(self, ws):
        self.recording_status = "OFF" # PAUSED, STOPPED, INTERRUPTED
        self.all_speech = np.array([], dtype = np.float32)
        self.previous_length = 0
        self.ws = ws
        self.setup_receiving()
   
    def setup_receiving(self):
        self.receiver_thread = threading.Thread(target = self.receive_audio).start()
        print("Receiving Thread Active")
        
    def receive_audio(self): # add a save on stop/pause parameter.
        self.recording_status = "ON"
        try: 
            while True:
                data = self.ws.receive()
                if data == "Pause":
                    self.recording_status = "PAUSED"
                    self.save_audio()
                elif data == "Stop": 
                    self.recording_status = "STOPPED"
                    self.save_audio()
                else:
                    audio = np.frombuffer(data, dtype = np.float32)
                    self.all_speech = np.append(self.all_speech, audio)

        except Exception as es:
            self.recording_status = "INTERRUPTED"
            return print(es)


    def save_audio(self):
        all_speech_int = (self.all_speech * 32767).astype(np.int16)
        audio_file = wave.open("output.wav", "wb")
        audio_file.setnchannels(1)
        audio_file.setsampwidth(2)
        audio_file.setframerate(16000)
        audio_file.writeframes(b''.join(all_speech_int))
        audio_file.close()

    def transcribe(self, online):
        chunk_length = 16384
        while self.recording_status == "ON" or self.recording_status == "PAUSED" or self.previous_length < len(self.all_speech):
            if self.previous_length < len(self.all_speech):
                length_of_new_frame = len(self.all_speech) - self.previous_length
                if length_of_new_frame >= chunk_length:
                    online.insert_audio_chunk(self.all_speech[self.previous_length:self.previous_length + chunk_length])
                    commited, rest = online.process_iter()
                    self.previous_length += chunk_length
                    try:
                        self.ws.send(f"{commited[2]} {rest[2]}")
                    except:
                        print("Could not send last block. Will send once connection is reopened")

                    
                elif chunk_length > length_of_new_frame > 0:
                    online.insert_audio_chunk(self.all_speech[self.previous_length:self.previous_length + length_of_new_frame])
                    self.previous_length += length_of_new_frame
                    if length_of_new_frame > 8 * 512:
                        commited, rest = online.process_iter()
                        
                        try:
                            self.ws.send(f"{commited[2]} {rest[2]}")
                        except:
                            print("Could not send last block. Will send once connection is reopened")
                        

        if self.recording_status == "STOPPED":
            online.init()
            self.all_speech = np.array([], dtype = np.float32)
            self.previous_length = 0

        return print("Websocket thread closed")
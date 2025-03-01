import numpy as np
import wave
import threading
import queue


class LiveTranscriberWS():
    def __init__(self, online):
        self.recording_status = "OFF" # PAUSED, STOPPED, INTERRUPTED
        self.all_speech = np.array([], dtype = np.float32)
        self.online = online
        self.audio_queue = queue.Queue(-1)
        self.session = 0
   
    def setup(self, ws, send_transcript = True):
        self.ws = ws
        self.send_transcript = send_transcript
        self.receiver_thread = threading.Thread(target = self.receive_audio)
        self.transcriber_thread = threading.Thread(target = self.transcribe)

        self.receiver_thread.start()
        self.transcriber_thread.start()
   
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
                    self.session += 1
                    self.audio_queue.put(self.session)
                    self.save_audio()
                    break
                else:
                    audio = np.frombuffer(data, dtype = np.float32)
                    self.audio_queue.put(audio)
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

    def transcribe(self):
        chunk_length = 16384
        self.commited = ""
        self.rest = ""
        while self.recording_status == "ON" or self.recording_status == "PAUSED" or not self.audio_queue.empty():
                try: 
                    audio = self.audio_queue.get(timeout = 1)
                    if isinstance(audio, int):
                        self.online.init()
                        self.all_speech = np.array([], np.float32)
                        print(f"Ending Session {audio}")
                        continue
                except queue.Empty:
                    continue
                
                if len(audio) >= chunk_length:
                    self.online.insert_audio_chunk(audio)
                    self.commited, self.rest = self.online.process_iter()
                    if self.send_transcript == True:
                        try:
                            self.ws.send(f"{self.commited[2]} {self.rest[2]}")
                        except:
                            print("Could not send last block. Will send once connection is reopened")
 
                elif chunk_length > len(audio) > 0:
                    self.online.insert_audio_chunk(audio)
                    if len(audio) > 8 * 512:
                        self.commited, self.rest = self.online.process_iter()
                        if self.send_transcript == True:
                            try:
                                self.ws.send(f"{self.commited[2]} {self.rest[2]}")
                            except:
                                print("Could not send last block. Will send once connection is reopened")
        return print("Transcribe Thread Closed")
    
import sys
import os
import keyboard
import time
import speech_recognition as sr
import sounddevice as sd
import soundfile as sf
import glob
import json
import threading
import re
import numpy as np
from groq import Groq

import live2d.v3 as live2d
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QRegion

from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

# ==========================================
# 1. KONFIGURASI KOGNITIF (GROQ)
# ==========================================
GROQ_API_KEY = "Masukkan API Key Groq Anda di sini"  
client = Groq(api_key=GROQ_API_KEY)

chat_history = [
    {
        "role": "system", 
        "content": (
            "Pembuatmu adalah Ricard. Kamu adalah A.R.O.N.A, asisten AI pribadi yang ceria, imut, dan peduli. "
            "Panggil pengguna dengan 'Sensei'. Gunakan bahasa Indonesia kasual (aku, kamu, sih, dong). "
            "Saat ini kamu berada dalam Fase 6: Ekspresi Wajah & PTT. Fokus utama adalah memberikan respons yang kaya secara emosional. "
            "PENTING: Kamu WAJIB merespons HANYA dalam format JSON baku dengan 3 kunci wajib: 'id', 'jp', dan 'emosi'. "
            "Contoh: {\"id\": \"Halo Sensei!\", \"jp\": \"先生、こんにちは！\", \"emosi\": \"senang\"} "
            "ATURAN MUTLAK: "
            "1. Kunci 'jp' WAJIB diisi. DILARANG KERAS menggunakan alfabet (A-Z) atau angka (0-9) di dalam teks 'jp'. Gunakan Katakana untuk kata asing. "
            "2. Sesuaikan nilai 'emosi' dengan isi teksmu."
        )
    }
]

# ==========================================
# 2. KONFIGURASI PITA SUARA (VOICEVOX)
# ==========================================
print("[SISTEM] Menjahit mesin ONNX, Kamus, dan Voice Models...")

ort_path = os.path.join("voicevox_core", "onnxruntime", "lib", Onnxruntime.LIB_VERSIONED_FILENAME)
ojt_path = os.path.join("voicevox_core", "dict", "open_jtalk_dic_utf_8-1.11")

ort_dir = os.path.abspath(os.path.dirname(ort_path))
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(ort_dir)

ort = Onnxruntime.load_once(filename=ort_path)
ojt = OpenJtalk(ojt_path)
core = Synthesizer(ort, ojt)

vvm_files = glob.glob(os.path.join("voicevox_core", "models", "vvms", "*.vvm"))
for vvm_file in vvm_files:
    with VoiceModelFile.open(vvm_file) as model:
        core.load_voice_model(model)

speaker_id = 8 # <- (ID Voice Model yang digunakan, Ubah sesuai yang diinginkan. Cek folder "voicevox_core/models/vvms" untuk daftar lengkap)

is_speaking = False
audio_data = None
audio_fs = 44100
audio_start_time = 0

# Status Emosi Global
target_emosi = "netral"

# PRESET 10 OTOT WAJAH LIVE2D
EMOSI_PRESETS = {
    "netral": {
        "ParamCheek": 0.0, "ParamMouthForm": 1.0, 
        "ParamEyeLSmile": 0.0, "ParamEyeRSmile": 0.0,
        "ParamBrowLY": 0.0, "ParamBrowRY": 0.0,
        "ParamBrowLAngle": 0.0, "ParamBrowRAngle": 0.0,
        "ParamBrowLForm": 0.0, "ParamBrowRForm": 0.0
    },
    "senang": {
        "ParamCheek": 0.4, "ParamMouthForm": 1.0, 
        "ParamEyeLSmile": 1.0, "ParamEyeRSmile": 1.0,
        "ParamBrowLY": 0.3, "ParamBrowRY": 0.3,
        "ParamBrowLAngle": 0.0, "ParamBrowRAngle": 0.0,
        "ParamBrowLForm": 0.0, "ParamBrowRForm": 0.0
    },
    "sedih": {
        "ParamCheek": 0.0, "ParamMouthForm": -1.0,
        "ParamEyeLSmile": 0.0, "ParamEyeRSmile": 0.0,
        "ParamBrowLY": -0.3, "ParamBrowRY": -0.3,
        "ParamBrowLAngle": -0.6, "ParamBrowRAngle": -0.6,
        "ParamBrowLForm": -1.0, "ParamBrowRForm": -1.0
    },
    "marah": {
        "ParamCheek": 0.2, "ParamMouthForm": -1.0, 
        "ParamEyeLSmile": 0.0, "ParamEyeRSmile": 0.0,
        "ParamBrowLY": -0.5, "ParamBrowRY": -0.5,
        "ParamBrowLAngle": 0.8, "ParamBrowRAngle": 0.8,
        "ParamBrowLForm": -1.0, "ParamBrowRForm": -1.0
    },
    "malu": {
        "ParamCheek": 1.0, "ParamMouthForm": 0.5,
        "ParamEyeLSmile": 0.5, "ParamEyeRSmile": 0.5,
        "ParamBrowLY": -0.2, "ParamBrowRY": -0.2,
        "ParamBrowLAngle": -0.4, "ParamBrowRAngle": -0.4,
        "ParamBrowLForm": 0.0, "ParamBrowRForm": 0.0
    }
}

# ==========================================
# 3. KUMPULAN FUNGSI SISTEM SARAF
# ==========================================
def ekstrak_json(teks_raw):
    try:
        awal = teks_raw.find('{')
        akhir = teks_raw.rfind('}') + 1
        if awal != -1 and akhir != 0:
            teks_json = teks_raw[awal:akhir]
            return json.loads(teks_json)
        return json.loads(teks_raw)
    except Exception as e:
        print(f"\n[DEBUG ERROR JSON] {e}\nRaw: {teks_raw}\n")
        return {"id": "Maaf Sensei, memoriku sedikit kacau.", "jp": "先生、ごめんなさい。", "emosi": "sedih"}

def arona_think(text_input):
    chat_history.append({"role": "user", "content": text_input})
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=chat_history,
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        jawaban_raw = completion.choices[0].message.content
        chat_history.append({"role": "assistant", "content": jawaban_raw})
        
        data = ekstrak_json(jawaban_raw)
        return data.get("id", ""), data.get("jp", ""), data.get("emosi", "netral")
    except Exception as e:
        print(f"[A.R.O.N.A] Error Kognitif: {e}")
        return "Otakku terputus, Sensei.", "接続が切れました。", "sedih"

def arona_speak_core(text_jp):
    global is_speaking, audio_data, audio_fs 
    
    if not text_jp:
        text_jp = "はい"
    
    text_jp_aman = re.sub(r'[a-zA-Z0-9\s\n\r!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?~`]', '', text_jp)
    
    text_jp_aman = text_jp_aman.lstrip('。、！？・…')
    
    if not re.search(r'[ぁ-んァ-ン一-龥]', text_jp_aman):
        text_jp_aman = "確認しました"
        
    print(f"[DEBUG SUARA] Membaca teks: {text_jp_aman}")
        
    output_file = "arona_voice_core.wav"
    try:
        audio_data_raw = core.tts(text_jp_aman, speaker_id) 
        with open(output_file, "wb") as f:
            f.write(audio_data_raw)

        data, fs = sf.read(output_file)
        if len(data.shape) > 1:
            data = data[:, 0]
            
        audio_data = data
        audio_fs = fs
        
        is_speaking = True
        sd.play(data, fs)
        sd.wait() 
        
    except Exception as e:
        print(f"[A.R.O.N.A] Kesalahan sintesis: {e}")
    finally:
        is_speaking = False
        if os.path.exists(output_file):
            try: os.remove(output_file)
            except: pass

def arona_listen(hotkey="alt+space"):
    fs = 44100  
    filename = "temp_input.wav"
    text_result = None
    rekaman = []
    
    print(f"\n[A.R.O.N.A] Telinga aktif.")
    print(f">>> TAHAN TOMBOL '{hotkey}' UNTUK MEREKAM SUARA. LEPASKAN JIKA SELESAI. <<<")
        
    try:
        with sd.InputStream(samplerate=fs, channels=1, dtype='float32') as stream:
            while keyboard.is_pressed(hotkey):
                data, overflowed = stream.read(1024)
                rekaman.append(data)
                
        if len(rekaman) > 0:
            rekaman_np = np.concatenate(rekaman, axis=0)
            sf.write(filename, rekaman_np, fs)
        else:
            return None
            
    except Exception as e:
        return None

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(filename) as source:
            audio_data_rec = recognizer.record(source)
            text_result = recognizer.recognize_google(audio_data_rec, language="id-ID")
            print(f"[Input Sensei] : {text_result}")
    except:
        print("[A.R.O.N.A] Suara tidak terdengar jelas.")

    if os.path.exists(filename):
        try: os.remove(filename)
        except: pass
            
    return text_result

def loop_sistem_ai():
    global target_emosi
    
    print("==================================================")
    print("Project A.R.O.N.A - FASE 6: EKSPRESI WAJAH & PTT")
    print("Status: Berjalan di Latar Belakang & Latar Depan")
    print("-> [Tahan Alt + Space] untuk berbicara")
    print("==================================================\n")
    
    try:
        while True:
            if keyboard.is_pressed('alt+space'):
                perintah_teks = arona_listen(hotkey="alt+space")
                if perintah_teks:
                    print("[A.R.O.N.A] Berpikir...")
                    teks_id, teks_jp, emosi_mentah = arona_think(perintah_teks)
                    
                    emosi = emosi_mentah.lower()
                    if emosi not in EMOSI_PRESETS:
                        emosi = "netral"
                        
                    target_emosi = emosi
                        
                    print(f"\n[A.R.O.N.A] ({emosi.upper()}): {teks_id}")

                    print(f"[DEBUG JP MENTAH] : {teks_jp}\n") 
                    
                    arona_speak_core(teks_jp)
                    
                    target_emosi = "netral"
                    print("-" * 50)
                time.sleep(0.5) 
                
            time.sleep(0.05) 
            
    except Exception as e:
        print(f"\n[Thread Error] {e}")

# ==========================================
# 4. DIMENSI FISIK (PyQt5 + Live2D)
# ==========================================
class AvatarWindow(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 800)
        self.model = None

        area_hitbox = QRegion(0, 200, 600, 600)
        self.setMask(area_hitbox)

        self.mulut_sekarang = 0.0
        self.waktu_mulai_bicara = 0.0
        self.status_bicara_sebelumnya = False
        
        self.otot_wajah = {k: 0.0 for k in EMOSI_PRESETS["netral"]}
        self.otot_wajah["ParamMouthForm"] = 1.0 

    def initializeGL(self):
        live2d.init()
        live2d.glInit()
        self.model = live2d.LAppModel()

        jalur_absolut = os.path.abspath(os.path.join("Avatar", "L2DZeroVS.model3.json"))
        jalur_aman_cpp = jalur_absolut.replace("\\", "/")
        
        self.model.LoadModelJson(jalur_aman_cpp)
        self.model.Resize(600, 800)

    def paintGL(self):
        live2d.clearBuffer()
        if self.model:
            self.model.Update()
            
            global is_speaking, audio_data, audio_fs, target_emosi
            
            target_otot = EMOSI_PRESETS[target_emosi]
            for nama_parameter, nilai_target in target_otot.items():
                self.otot_wajah[nama_parameter] += (nilai_target - self.otot_wajah[nama_parameter]) * 0.1
                self.model.SetParameterValue(nama_parameter, self.otot_wajah[nama_parameter])
            
            if is_speaking and not self.status_bicara_sebelumnya:
                self.waktu_mulai_bicara = time.time()
                
            self.status_bicara_sebelumnya = is_speaking

            if is_speaking and audio_data is not None:
                elapsed = time.time() - self.waktu_mulai_bicara
                current_frame = int(elapsed * audio_fs)
                window_size = 2048 
                
                if current_frame < len(audio_data):
                    start_idx = max(0, current_frame - (window_size // 2))
                    end_idx = min(len(audio_data), current_frame + (window_size // 2))
                    chunk = audio_data[start_idx:end_idx]
                    
                    if len(chunk) > 0:
                        rms = np.sqrt(np.mean(chunk**2))
                        target_buka = min(1.0, float(rms) * 12.0) 
                    else: target_buka = 0.0
                else: target_buka = 0.0
            else: target_buka = 0.0
                
            self.mulut_sekarang += (target_buka - self.mulut_sekarang) * 0.5
            self.model.SetParameterValue("ParamMouthOpenY", self.mulut_sekarang)
                
            self.model.Draw()

    def timerEvent(self, event):
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.titik_awal_drag = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            posisi_baru = event.globalPos() - self.titik_awal_drag
            self.move(posisi_baru)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            layar = QApplication.primaryScreen().geometry()
            x_sekarang = self.x()
            y_sekarang = self.y()
            batas_kanan = layar.width() - self.width()
            batas_bawah = layar.height() - self.height()
            x_aman = max(0, min(x_sekarang, batas_kanan))
            y_aman = max(0, min(y_sekarang, batas_bawah))
            if x_sekarang != x_aman or y_sekarang != y_aman:
                self.move(x_aman, y_aman)
            event.accept()

if __name__ == "__main__":
    ai_thread = threading.Thread(target=loop_sistem_ai, daemon=True)
    ai_thread.start()

    app = QApplication(sys.argv)
    window = AvatarWindow()
    window.startTimer(1000 // 60)
    window.show()
    
    sys.exit(app.exec_())
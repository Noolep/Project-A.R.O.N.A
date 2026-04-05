# Project A.R.O.N.A (Artificial Real-time Observer & Neural Assistant)

Asisten AI virtual desktop otonom yang ditenagai oleh Groq (Llama 3.3), Voicevox (Native TTS Jepang), dan Live2D. Dirancang untuk menjadi asisten produktivitas dengan interaksi suara *real-time*.

## 🌟 Fitur Utama
* **Push-To-Talk (PTT)**: Komunikasi audio dua arah secara dinamis. Tahan `Alt + Space` untuk berbicara dengan A.R.O.N.A.
* **Smart Emotion Sync**: AI menentukan sendiri emosinya (Senang, Sedih, Marah, Malu, Netral) dari konteks pembicaraan dan secara otomatis menggerakkan parameter otot wajah Live2D.
* **Audio-Amplitude Lip-Sync**: Sinkronisasi pergerakan bibir yang presisi berdasarkan gelombang RMS (Root Mean Square) dari suara yang dihasilkan.
* **Anti-Mute Firewall**: Sistem kebal terhadap *crash* (seperti *No Phoneme*) berkat Regex *Filtering* bahasa Jepang yang menyapu bersih halusinasi model AI.

---

## 🛠️ Persyaratan Sistem & Instalasi

Jika Anda melakukan *clone/download* langsung dari *source code* ini, Anda harus menyiapkan aset pihak ketiga (Voicevox & Live2D) secara manual.

### 1. Install Dependencies
Pastikan Python 3.10 atau 3.11 sudah terpasang. Buka terminal (Run as Administrator) dan jalankan:
```bash
pip install -r requirements.txt
```
### 2. Konfigurasi Groq API Key
 1. Dapatkan API Key secara gratis di [Groq Console.](https://console.groq.com/keys)
 2. Buka fail `arona.py.`
 3. Cari variabel `GROQ_API_KEY` dan tempelkan API Key Anda.

### 3. Setup Mesin Voicevox Core
 1. Unduh **Voicevox Core SDK** dari [GitHub Resmi Voicevox.](https://github.com/VOICEVOX/voicevox_core/releases)
 2. Unduh **Open JTalk Dictionary.**
 3. Unduh **Voice Model (.vvm)** pilihan Anda
 4. Buat folder `voicevox_core` di root proyek ini dan susun sesuai dengan struktur path yang ada di `arona.py.`

### 4. Setup Model Avatar (Live2D)
 1. Buat folder bernama `Avatar` di root proyek.
 2. Masukkan semua komponen Live2D Anda (`.model3.json`, `.moc3`, dan folder tekstur) ke dalamnya. Pastikan nama fail utamanya adalah `L2DZeroVS.model3.json` atau sesuaikan path-nya di dalam `arona.py`.

### 🚀 Menjalankan Aplikasi
Library pembaca input keyboard global membutuhkan izin akses sistem. Selalu jalankan terminal dengan hak akses **Administrator**.
```bash
python arona.py
```
### ⚖️ Lisensi
Didistribusikan di bawah lisensi MIT. Lihat file `LICENSE` untuk informasi lebih lanjut.

## 🤝 Kolaborasi & Pengembangan Lanjut
Proyek ini masih dalam tahap pengembangan aktif. Jika Anda tertarik untuk berkontribusi, menambahkan fitur baru (seperti *Agentic System* atau RAG), atau mengembangkan proyek ini lebih jauh, **silakan hubungi saya sebagai pembuat project ini untuk berdiskusi!** Anda bisa membuka *Issues*, *Pull Requests*, atau menghubungi kontak saya secara langsung.

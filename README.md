# /proyek_spk/README.md

# SPK Pemilihan Ekspedisi - Metode SAW

Ini adalah aplikasi web sederhana yang dibuat dengan Python dan Flask untuk mendemonstrasikan Sistem Pendukung Keputusan (SPK) dalam memilih ekspedisi pengiriman terbaik menggunakan metode **Simple Additive Weighting (SAW)**.

## Fitur

- **Dashboard**: Menampilkan rekomendasi ekspedisi terbaik beserta peringkat lengkap.
- **Data Alternatif**: Menampilkan daftar semua ekspedisi yang menjadi pilihan.
- **Data Kriteria**: Menampilkan kriteria yang digunakan untuk evaluasi beserta bobot dan tipenya (cost/benefit).
- **Input Nilai**: Menampilkan matriks evaluasi (nilai setiap alternatif untuk setiap kriteria).
- **Hasil Perhitungan**: Menampilkan proses perhitungan metode SAW langkah demi langkah, mulai dari matriks keputusan, normalisasi, hingga hasil akhir.

## Teknologi

- Backend: Python 3
- Framework: Flask
- Frontend: HTML, Bootstrap 5

## Cara Menjalankan Proyek

Pastikan Anda memiliki Python 3.6+ terinstal di komputer Anda.

**1. Clone atau Unduh Proyek**

Salin semua file proyek ini ke dalam sebuah folder bernama `proyek_spk`.

**2. Buka Terminal atau Command Prompt**

Arahkan terminal ke folder proyek yang baru Anda buat.
```bash
cd path/to/proyek_spk
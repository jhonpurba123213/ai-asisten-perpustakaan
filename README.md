# AI Asisten Perpustakaan Kampus

## 1. Deskripsi Aplikasi
AI Asisten Perpustakaan Kampus merupakan aplikasi berbasis web yang dikembangkan untuk membantu pengguna memperoleh informasi mengenai koleksi buku dan dokumen perpustakaan dengan memanfaatkan teknologi Artificial Intelligence (AI).

Aplikasi ini menggunakan Streamlit sebagai antarmuka, MySQL sebagai database buku, Ollama sebagai model AI, serta ChromaDB untuk menyimpan embedding dokumen dalam penerapan Retrieval-Augmented Generation (RAG).

## 2. Tujuan Aplikasi
- Mempermudah pencarian informasi buku.
- Memberikan rekomendasi buku.
- Membantu pengelolaan koleksi buku.
- Memungkinkan pengguna bertanya mengenai isi dokumen PDF melalui Chat AI.
- Mengintegrasikan database dan teknologi AI dalam satu aplikasi.

## 3. Fitur Aplikasi
1. Login Admin
2. Dashboard Perpustakaan
3. Chat AI
4. Pencarian Buku
5. Rekomendasi Buku
6. Kelola Buku (CRUD)
7. Upload Dokumen PDF
8. Retrieval-Augmented Generation (RAG)
9. Jam Operasional Perpustakaan
10. Informasi Perpustakaan

## 4. Teknologi yang Digunakan
- Python
- Streamlit
- MySQL
- XAMPP
- Ollama
- Qwen 2.5:3B
- Nomic Embed Text
- ChromaDB
- PyPDF

## 5. Struktur Folder
```text
AI-Perpustakaan/
├── app.py
├── app_backup.py
├── ai_perpustakaan.sql
├── README.md
├── uploads/
├── uploads_backup/
├── vectorstore/
└── vectorstore_backup/
```

## 6. Instalasi dan Menjalankan Aplikasi
1. Instal Python.
2. Instal XAMPP dan aktifkan MySQL.
3. Instal Ollama.
4. Unduh model AI:
   - ollama pull qwen2.5:3b
   - ollama pull nomic-embed-text
5. Siapkan database MySQL bernama ai_perpustakaan.
6. Instal library yang dibutuhkan.
7. Jalankan aplikasi menggunakan perintah:

```bash
python -m streamlit run app.py
```

## 7. Alur Kerja RAG
1. Admin mengunggah dokumen PDF.
2. Sistem mengekstraksi teks dari PDF.
3. Teks dibagi menjadi beberapa potongan (chunking).
4. Nomic Embed Text mengubah potongan teks menjadi embedding.
5. Embedding disimpan di ChromaDB.
6. Pengguna mengajukan pertanyaan melalui Chat AI.
7. Sistem mencari potongan dokumen yang relevan.
8. Konteks dikirim ke Ollama.
9. Qwen 2.5:3B menghasilkan jawaban berdasarkan konteks yang ditemukan.

## 8. Database
Nama database: `ai_perpustakaan`

Tabel utama: `buku`

Database digunakan untuk menyimpan informasi koleksi buku perpustakaan.

## 9. Backup
Backup proyek meliputi:
- File kode aplikasi.
- Database MySQL dalam format SQL.
- Dokumen PDF.
- Penyimpanan embedding ChromaDB.

## 10. Pengembang
Kelompok 4  
1. 233303030267 - Jhon Prasetyo Purba
2. 233303030304 - Mikael Hotasi Mangunsong
3. 233303030274 - Agus Berhasil Ndruru 
4. 233303030314 - Yuna Yeneskia Sembiring
5. 233303030288 - Roy Priman Ramajaya Sipayung
6. 233303030280 - Rui Monis
Program Studi Teknik Informatika  
Fakultas Sains dan Teknologi  
Universitas Prima Indonesia

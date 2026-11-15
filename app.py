
import os
import re
import html
import hashlib
import hmac
import requests
import streamlit as st
import mysql.connector

from pypdf import PdfReader
from chromadb import PersistentClient


# =====================================================
# 1. KONFIGURASI
# =====================================================

st.set_page_config(
    page_title="AI Asisten Perpustakaan",
    page_icon="📚",
    layout="wide"
)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "ai_perpustakaan",
    "port": 3306
}

OLLAMA_URL = "http://localhost:11434"
CHAT_MODEL = "qwen2.5:3b"
EMBED_MODEL = "nomic-embed-text"

FOLDER_UPLOAD = "uploads"
FOLDER_VECTOR = "vectorstore"

os.makedirs(FOLDER_UPLOAD, exist_ok=True)
os.makedirs(FOLDER_VECTOR, exist_ok=True)

USERNAME_ADMIN = st.secrets["ADMIN_USERNAME"]

PASSWORD_HASH_ADMIN = hashlib.sha256(
    st.secrets["ADMIN_PASSWORD"].encode()
).hexdigest()


# =====================================================
# 2. CHROMADB
# =====================================================

chroma_client = PersistentClient(path=FOLDER_VECTOR)

collection = chroma_client.get_or_create_collection(
    name="dokumen_perpustakaan"
)


# =====================================================
# 3. TEMA
# =====================================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(
        135deg, #fffdf2, #fff8d9, #fffef7
    );
    color: #403510;
}

[data-testid="stSidebar"] {
    background: linear-gradient(
        160deg, #7a5b00, #b8860b, #e0b323
    );
}

[data-testid="stSidebar"] * {
    color: white;
}

.main-title {
    color: #805d00;
    font-size: 34px;
    font-weight: 850;
    margin-bottom: 8px;
}

.subtitle {
    color: #837344;
    margin-bottom: 25px;
}

.book-card, .stat-card {
    background: white;
    padding: 20px;
    border-radius: 16px;
    border: 1px solid #f0dfa0;
    box-shadow: 0 6px 20px rgba(128,93,0,0.07);
    margin-bottom: 15px;
}

.book-title {
    color: #805d00;
    font-size: 19px;
    font-weight: bold;
}

.book-info {
    color: #685b37;
    line-height: 1.9;
}

.stat-number {
    color: #805d00;
    font-size: 30px;
    font-weight: bold;
}

div.stButton > button {
    background: linear-gradient(135deg, #e5b800, #a77b00);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: bold;
}

div.stButton > button:hover {
    color: white;
    border: none;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# 4. DATABASE MYSQL
# =====================================================

def koneksi_database():
    return mysql.connector.connect(**DB_CONFIG)


def ambil_semua_buku():
    conn = None
    cursor = None

    try:
        conn = koneksi_database()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM buku ORDER BY id_buku DESC"
        )

        return cursor.fetchall()

    except Exception as e:
        st.error(f"Database error: {e}")
        return []

    finally:
        if cursor:
            cursor.close()

        if conn and conn.is_connected():
            conn.close()


# =====================================================
# 5. LOGIN
# =====================================================

def halaman_login():

    st.markdown("<br><br>", unsafe_allow_html=True)

    kiri, tengah, kanan = st.columns([1, 1.2, 1])

    with tengah:

        st.markdown(
            "<h1 style='text-align:center;color:#805d00'>"
            "📚 AI Perpustakaan</h1>",
            unsafe_allow_html=True
        )

        st.write(
            "Selamat datang di AI Asisten Perpustakaan."
        )

        with st.form("form_login"):

            username = st.text_input("Username")

            password = st.text_input(
                "Password",
                type="password"
            )

            masuk = st.form_submit_button(
                "🔐 Login",
                use_container_width=True
            )

            if masuk:

                password_hash = hashlib.sha256(
                    password.encode()
                ).hexdigest()

                if (
                    hmac.compare_digest(
                        username, USERNAME_ADMIN
                    )
                    and hmac.compare_digest(
                        password_hash,
                        PASSWORD_HASH_ADMIN
                    )
                ):

                    st.session_state["admin_authenticated"] = True
                    st.session_state["nama"] = username

                    st.rerun()

                else:
                    st.error("Username atau password salah.")


if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
    halaman_login()
    st.stop()


# =====================================================
# 6. FUNGSI EMBEDDING OLLAMA
# =====================================================

def buat_embedding(teks):

    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": EMBED_MODEL,
            "input": teks
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return data["embeddings"][0]


# =====================================================
# 7. MEMBACA DAN MEMECAH PDF
# =====================================================

def pecah_teks(teks, ukuran=800, overlap=150):

    teks = re.sub(r"\s+", " ", teks).strip()

    potongan = []

    awal = 0

    while awal < len(teks):

        akhir = awal + ukuran

        bagian = teks[awal:akhir].strip()

        if bagian:
            potongan.append(bagian)

        awal += ukuran - overlap

    return potongan


# =====================================================
# 8. PROSES PDF KE CHROMADB
# =====================================================

def proses_pdf(file_pdf):

    reader = PdfReader(file_pdf)

    semua_teks = []

    for nomor, halaman in enumerate(reader.pages, start=1):

        teks = halaman.extract_text()

        if teks:
            semua_teks.append(
                f"Halaman {nomor}: {teks}"
            )

    teks_lengkap = "\n".join(semua_teks)

    if not teks_lengkap.strip():
        raise ValueError(
            "PDF tidak memiliki teks yang dapat dibaca. "
            "PDF hasil scan mungkin memerlukan OCR."
        )

    potongan = pecah_teks(teks_lengkap)

    nama_file = os.path.basename(file_pdf.name)

    ids_lama = collection.get(
        where={"nama_file": nama_file}
    )

    if ids_lama["ids"]:
        collection.delete(ids=ids_lama["ids"])

    daftar_id = []
    daftar_teks = []
    daftar_embedding = []
    daftar_metadata = []

    for nomor, potongan_teks in enumerate(potongan):

        embedding = buat_embedding(potongan_teks)

        daftar_id.append(
            f"{nama_file}_{nomor}_{hashlib.md5(potongan_teks.encode()).hexdigest()[:8]}"
        )

        daftar_teks.append(potongan_teks)

        daftar_embedding.append(embedding)

        daftar_metadata.append({
            "nama_file": nama_file,
            "nomor_potongan": nomor + 1
        })

    if daftar_id:

        collection.add(
            ids=daftar_id,
            documents=daftar_teks,
            embeddings=daftar_embedding,
            metadatas=daftar_metadata
        )

    return len(potongan)


# =====================================================
# 9. PENCARIAN RAG
# =====================================================

def cari_konteks_pdf(pertanyaan, jumlah=4):

    if collection.count() == 0:
        return []

    embedding_pertanyaan = buat_embedding(pertanyaan)

    hasil = collection.query(
        query_embeddings=[embedding_pertanyaan],
        n_results=min(jumlah, collection.count())
    )

    dokumen = hasil.get("documents", [[]])[0]
    metadata = hasil.get("metadatas", [[]])[0]

    konteks = []

    for teks, info in zip(dokumen, metadata):

        konteks.append({
            "teks": teks,
            "nama_file": info.get("nama_file", "Dokumen"),
            "nomor_potongan": info.get("nomor_potongan", "-")
        })

    return konteks


# =====================================================
# 10. FUNGSI CHAT AI DENGAN RAG
# =====================================================

def tanya_ai(pertanyaan, riwayat, buku):

    data_buku = []

    for b in buku:

        data_buku.append(
            f"Judul: {b['judul']}; "
            f"Penulis: {b['penulis']}; "
            f"Kategori: {b['kategori']}; "
            f"Stok: {b['stok']}"
        )

    konteks_buku = "\n".join(data_buku)

    konteks_pdf = cari_konteks_pdf(pertanyaan)

    teks_pdf = ""

    for item in konteks_pdf:

        teks_pdf += (
            f"\nSumber: {item['nama_file']}, "
            f"potongan {item['nomor_potongan']}\n"
            f"{item['teks']}\n"
        )

    system_prompt = f"""
Kamu adalah AI Asisten Perpustakaan.

Jawab menggunakan bahasa Indonesia yang jelas dan sopan.

ATURAN:
1. Gunakan data buku MySQL untuk pertanyaan koleksi buku.
2. Jangan mengarang judul buku atau stok.
3. Gunakan konteks PDF untuk menjawab pertanyaan isi dokumen.
4. Jika informasi tidak ditemukan dalam konteks PDF,
   katakan bahwa informasi belum ditemukan.
5. Jika menggunakan informasi PDF, sebutkan nama sumbernya.
6. Bedakan informasi dari database buku dan informasi PDF.

DATA BUKU MYSQL:
{konteks_buku}

KONTEKS DOKUMEN PDF:
{teks_pdf if teks_pdf else "Tidak ditemukan konteks PDF yang relevan."}
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(riwayat[-8:])

    messages.append({
        "role": "user",
        "content": pertanyaan
    })

    try:

        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": CHAT_MODEL,
                "messages": messages,
                "stream": False
            },
            timeout=180
        )

        response.raise_for_status()

        return response.json()["message"]["content"]

    except requests.exceptions.ConnectionError:

        return "Ollama tidak berjalan. Silakan jalankan Ollama."

    except requests.exceptions.Timeout:

        return "AI membutuhkan waktu terlalu lama. Coba lagi."

    except Exception as e:

        return f"Terjadi kesalahan: {e}"


# =====================================================
# 11. SIDEBAR
# =====================================================

if "menu_utama" not in st.session_state:
    st.session_state["menu_utama"] = "Dashboard"

if "riwayat_chat" not in st.session_state:
    st.session_state["riwayat_chat"] = []

with st.sidebar:

    st.markdown("# 📚 AI Perpus")
    st.markdown("### Asisten Perpustakaan")

    st.write("---")

    st.write(
        f"👤 Login sebagai: **{st.session_state['nama']}**"
    )

    menu = st.radio(
        "MENU UTAMA",
        [
            "Dashboard",
            "Chat AI",
            "Cari Buku",
            "Rekomendasi Buku",
            "Kelola Buku",
            "Upload PDF",
            "Jam Operasional Perpustakaan",
            "Informasi Perpustakaan"
        ],
        key="menu_utama"
    )

    st.write("---")

    st.caption("Streamlit • Ollama • MySQL • ChromaDB • RAG")

    if st.button("🚪 Logout", use_container_width=True):

        st.session_state["admin_authenticated"] = False
        st.session_state["riwayat_chat"] = []

        st.rerun()


buku_list = ambil_semua_buku()


# =====================================================
# 12. DASHBOARD
# =====================================================

if menu == "Dashboard":

    st.markdown(
        '<div class="main-title">Dashboard Perpustakaan 📚</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Selamat datang di AI Asisten Perpustakaan.'
        '</div>',
        unsafe_allow_html=True
    )

    total_stok = sum(
        int(b["stok"] or 0) for b in buku_list
    )

    jumlah_pdf = len([
        f for f in os.listdir(FOLDER_UPLOAD)
        if f.lower().endswith(".pdf")
    ])

    kolom = st.columns(4)

    statistik = [
        ("Total Buku", len(buku_list)),
        ("Total Stok", total_stok),
        ("Dokumen PDF", jumlah_pdf),
        ("Potongan RAG", collection.count())
    ]

    for col, (label, angka) in zip(kolom, statistik):

        with col:

            st.markdown(
                f"""
                <div class="stat-card">
                    <b>{label}</b>
                    <div class="stat-number">{angka}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.info(
        "Gunakan menu di sebelah kiri untuk mencari buku, "
        "mengelola koleksi, dan bertanya kepada AI."
    )


# =====================================================
# 13. CHAT AI
# =====================================================

elif menu == "Chat AI":

    st.markdown(
        '<div class="main-title">💬 Chat AI Perpustakaan</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Tanyakan koleksi buku atau isi dokumen PDF.'
        '</div>',
        unsafe_allow_html=True
    )

    for chat in st.session_state["riwayat_chat"]:

        with st.chat_message(chat["role"]):
            st.markdown(chat["content"])

    pesan = st.chat_input(
        "Tulis pertanyaan kamu di sini..."
    )

    if pesan:

        st.session_state["riwayat_chat"].append({
            "role": "user",
            "content": pesan
        })

        with st.chat_message("user"):
            st.markdown(pesan)

        with st.chat_message("assistant"):

            with st.spinner("AI sedang mencari informasi..."):

                jawaban = tanya_ai(
                    pesan,
                    st.session_state["riwayat_chat"][:-1],
                    buku_list
                )

                st.markdown(jawaban)

        st.session_state["riwayat_chat"].append({
            "role": "assistant",
            "content": jawaban
        })

    if st.button("🗑️ Hapus Riwayat Chat"):

        st.session_state["riwayat_chat"] = []

        st.rerun()


# =====================================================
# 14. CARI BUKU
# =====================================================

elif menu == "Cari Buku":

    st.markdown(
        '<div class="main-title">🔎 Cari Buku</div>',
        unsafe_allow_html=True
    )

    kata_kunci = st.text_input(
        "Masukkan judul, penulis, atau kategori buku"
    )

    if st.button("🔍 Cari Buku"):

        hasil = [
            b for b in buku_list
            if kata_kunci.lower() in " ".join([
                str(b["judul"]),
                str(b["penulis"]),
                str(b["kategori"]),
                str(b["penerbit"])
            ]).lower()
        ]

        if not kata_kunci.strip():

            st.warning("Masukkan kata kunci terlebih dahulu.")

        elif hasil:

            st.success(f"Ditemukan {len(hasil)} buku.")

            for b in hasil:

                st.markdown(
                    f"""
                    <div class="book-card">
                        <div class="book-title">
                            📘 {html.escape(str(b['judul']))}
                        </div>
                        <div class="book-info">
                            Penulis: {html.escape(str(b['penulis']))}<br>
                            Kategori: {html.escape(str(b['kategori']))}<br>
                            Penerbit: {html.escape(str(b['penerbit']))}<br>
                            Tahun: {b['tahun_terbit']}<br>
                            Stok: {b['stok']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        else:

            st.warning("Buku tidak ditemukan.")


# =====================================================
# 15. REKOMENDASI BUKU
# =====================================================

elif menu == "Rekomendasi Buku":

    st.markdown(
        '<div class="main-title">✨ Rekomendasi Buku</div>',
        unsafe_allow_html=True
    )

    kategori = sorted(set(
        str(b["kategori"]) for b in buku_list
    ))

    pilihan = st.selectbox(
        "Pilih kategori",
        ["Semua Kategori"] + kategori
    )

    if st.button("Tampilkan Rekomendasi"):

        hasil = [
            b for b in buku_list
            if pilihan == "Semua Kategori"
            or str(b["kategori"]) == pilihan
        ]

        if hasil:

            for b in hasil:

                st.markdown(
                    f"""
                    <div class="book-card">
                        <div class="book-title">
                            📘 {html.escape(str(b['judul']))}
                        </div>
                        <div class="book-info">
                            Penulis: {html.escape(str(b['penulis']))}<br>
                            Kategori: {html.escape(str(b['kategori']))}<br>
                            Stok: {b['stok']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        else:

            st.info("Belum ada buku untuk kategori tersebut.")


# =====================================================
# 16. KELOLA BUKU
# =====================================================

elif menu == "Kelola Buku":

    st.markdown(
        '<div class="main-title">🛠️ Kelola Buku</div>',
        unsafe_allow_html=True
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Daftar Buku",
        "Tambah Buku",
        "Edit Buku",
        "Hapus Buku"
    ])

    # DAFTAR
    with tab1:

        data = ambil_semua_buku()

        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True
        )

    # TAMBAH
    with tab2:

        with st.form("form_tambah"):

            judul = st.text_input("Judul")
            penulis = st.text_input("Penulis")
            kategori = st.text_input("Kategori")

            tahun = st.number_input(
                "Tahun Terbit", 1000, 9999, 2026
            )

            penerbit = st.text_input("Penerbit")
            stok = st.number_input("Stok", 0, 100000, 1)

            simpan = st.form_submit_button("Simpan Buku")

        if simpan:

            if not all([
                judul.strip(),
                penulis.strip(),
                kategori.strip(),
                penerbit.strip()
            ]):

                st.warning("Semua kolom harus diisi.")

            else:

                conn = None
                cursor = None

                try:

                    conn = koneksi_database()
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        INSERT INTO buku
                        (judul, penulis, kategori,
                         tahun_terbit, penerbit, stok)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            judul.strip(),
                            penulis.strip(),
                            kategori.strip(),
                            int(tahun),
                            penerbit.strip(),
                            int(stok)
                        )
                    )

                    conn.commit()

                    st.success(
                        f"Buku berhasil ditambahkan! ID: {cursor.lastrowid}"
                    )

                    st.info(
                        "Silakan buka tab Daftar Buku untuk melihat data."
                    )

                except Exception as e:

                    if conn:
                        conn.rollback()

                    st.error(f"Gagal menambahkan buku: {e}")

                finally:

                    if cursor:
                        cursor.close()

                    if conn and conn.is_connected():
                        conn.close()

    # EDIT
    with tab3:

        data_edit = ambil_semua_buku()

        if data_edit:

            pilihan_edit = st.selectbox(
                "Pilih buku",
                data_edit,
                format_func=lambda b: (
                    f"{b['id_buku']} - {b['judul']}"
                )
            )

            with st.form("form_edit"):

                judul_edit = st.text_input(
                    "Judul",
                    value=pilihan_edit["judul"]
                )

                penulis_edit = st.text_input(
                    "Penulis",
                    value=pilihan_edit["penulis"]
                )

                kategori_edit = st.text_input(
                    "Kategori",
                    value=pilihan_edit["kategori"]
                )

                tahun_edit = st.number_input(
                    "Tahun Terbit",
                    min_value=1000,
                    max_value=9999,
                    value=int(pilihan_edit["tahun_terbit"])
                )

                penerbit_edit = st.text_input(
                    "Penerbit",
                    value=pilihan_edit["penerbit"]
                )

                stok_edit = st.number_input(
                    "Stok",
                    min_value=0,
                    value=int(pilihan_edit["stok"])
                )

                tombol_edit = st.form_submit_button(
                    "Simpan Perubahan"
                )

            if tombol_edit:

                conn = None
                cursor = None

                try:

                    conn = koneksi_database()
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        UPDATE buku
                        SET judul=%s,
                            penulis=%s,
                            kategori=%s,
                            tahun_terbit=%s,
                            penerbit=%s,
                            stok=%s
                        WHERE id_buku=%s
                        """,
                        (
                            judul_edit.strip(),
                            penulis_edit.strip(),
                            kategori_edit.strip(),
                            int(tahun_edit),
                            penerbit_edit.strip(),
                            int(stok_edit),
                            pilihan_edit["id_buku"]
                        )
                    )

                    conn.commit()

                    st.success("Data buku berhasil diperbarui!")

                except Exception as e:

                    if conn:
                        conn.rollback()

                    st.error(f"Gagal mengedit buku: {e}")

                finally:

                    if cursor:
                        cursor.close()

                    if conn and conn.is_connected():
                        conn.close()

        else:

            st.info("Belum ada buku untuk diedit.")

    # HAPUS
    with tab4:

        data_hapus = ambil_semua_buku()

        if data_hapus:

            pilihan_hapus = st.selectbox(
                "Pilih buku yang akan dihapus",
                data_hapus,
                format_func=lambda b: (
                    f"{b['id_buku']} - {b['judul']}"
                )
            )

            konfirmasi = st.checkbox(
                "Saya yakin ingin menghapus buku ini."
            )

            if st.button("🗑️ Hapus Buku"):

                if not konfirmasi:

                    st.warning("Centang konfirmasi terlebih dahulu.")

                else:

                    conn = None
                    cursor = None

                    try:

                        conn = koneksi_database()
                        cursor = conn.cursor()

                        cursor.execute(
                            "DELETE FROM buku WHERE id_buku=%s",
                            (pilihan_hapus["id_buku"],)
                        )

                        conn.commit()

                        st.success("Buku berhasil dihapus.")

                    except Exception as e:

                        if conn:
                            conn.rollback()

                        st.error(f"Gagal menghapus buku: {e}")

                    finally:

                        if cursor:
                            cursor.close()

                        if conn and conn.is_connected():
                            conn.close()

        else:

            st.info("Tidak ada buku untuk dihapus.")


# =====================================================
# 17. UPLOAD PDF DAN INDEXING RAG
# =====================================================

elif menu == "Upload PDF":

    st.markdown(
        '<div class="main-title">📄 Upload Dokumen PDF</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Unggah dokumen untuk diproses dan digunakan AI.'
        '</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Dokumen PDF akan dibaca, dipecah menjadi potongan teks, "
        "dibuat embedding, lalu disimpan ke ChromaDB."
    )

    file_pdf = st.file_uploader(
        "Pilih dokumen PDF",
        type=["pdf"]
    )

    if file_pdf:

        st.write(f"Nama file: {file_pdf.name}")

        if st.button("📥 Proses dan Simpan PDF"):

            try:

                jalur = os.path.join(
                    FOLDER_UPLOAD,
                    os.path.basename(file_pdf.name)
                )

                with open(jalur, "wb") as f:
                    f.write(file_pdf.getbuffer())

                with st.spinner(
                    "Membaca PDF dan membuat embedding..."
                ):

                    jumlah = proses_pdf(file_pdf)

                st.success(
                    f"PDF berhasil diproses! "
                    f"{jumlah} potongan disimpan ke ChromaDB."
                )

            except Exception as e:

                st.error(f"Gagal memproses PDF: {e}")

    st.divider()

    st.subheader("📚 Dokumen yang Tersimpan")

    daftar_pdf = [
        nama for nama in os.listdir(FOLDER_UPLOAD)
        if nama.lower().endswith(".pdf")
    ]

    if daftar_pdf:

        for nama in daftar_pdf:
            st.write("📄", nama)

    else:

        st.info("Belum ada dokumen PDF.")


# =====================================================
# 18. JAM OPERASIONAL PERPUSTAKAAN
# =====================================================

elif menu == "Jam Operasional Perpustakaan":

    from datetime import datetime, time

    st.markdown(
        '<div class="main-title">'
        '🕒 Jam Operasional Perpustakaan'
        '</div>',
        unsafe_allow_html=True
    )

    # Mengambil hari dan waktu dari komputer yang menjalankan aplikasi.
    # Pastikan zona waktu Windows diatur ke (UTC+07:00) Bangkok, Hanoi, Jakarta.
    sekarang = datetime.now()

    nama_hari = [
        "Senin", "Selasa", "Rabu",
        "Kamis", "Jumat", "Sabtu", "Minggu"
    ]

    hari_ini = nama_hari[sekarang.weekday()]
    waktu_sekarang = sekarang.time()

    # Jadwal operasional perpustakaan
    jadwal = {
        "Senin": (time(8, 0), time(20, 0)),
        "Selasa": (time(8, 0), time(20, 0)),
        "Rabu": (time(8, 0), time(20, 0)),
        "Kamis": (time(8, 0), time(20, 0)),
        "Jumat": (time(8, 0), time(20, 0)),
        "Sabtu": (time(8, 0), time(14, 0)),
        "Minggu": None
    }

    jam_hari_ini = jadwal[hari_ini]

    if jam_hari_ini is not None:
        jam_buka, jam_tutup = jam_hari_ini

        if jam_buka <= waktu_sekarang < jam_tutup:
            status = "BUKA"
            warna = "#198754"
            pesan = "Perpustakaan sedang beroperasi."
        else:
            status = "TUTUP"
            warna = "#dc3545"
            pesan = "Perpustakaan sedang tidak beroperasi."
    else:
        status = "TUTUP"
        warna = "#dc3545"
        pesan = "Perpustakaan tutup pada hari Minggu."

    # Menampilkan status otomatis berdasarkan hari dan jam saat ini.
    st.markdown(
        f"""
        <div style="
            background:white;
            padding:25px;
            border-radius:16px;
            border:1px solid #f0dfa0;
            margin-bottom:20px;
        ">
            <h2 style="color:#805d00;">📅 Hari ini: {hari_ini}</h2>
            <h1 style="color:{warna};">● {status}</h1>
            <p style="color:#685b37;">{pesan}</p>
            <p style="color:#685b37;">
                Waktu sekarang: {sekarang.strftime("%H:%M:%S")} WIB
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Menampilkan jadwal operasional selama satu minggu.
    st.subheader("📋 Jadwal Operasional Mingguan")

    for hari, jam in jadwal.items():

        if jam is None:
            keterangan = "Tutup"
        else:
            buka, tutup = jam
            keterangan = (
                f"{buka.strftime('%H.%M')}–"
                f"{tutup.strftime('%H.%M')} WIB"
            )

        penanda = "📍 Hari Ini" if hari == hari_ini else ""

        st.markdown(
            f"""
            <div class="book-card">
                <div class="book-title">📅 {hari} {penanda}</div>
                <div class="book-info">🕒 {keterangan}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# =====================================================
# 19. INFORMASI PERPUSTAKAAN
# =====================================================

elif menu == "Informasi Perpustakaan":

    st.markdown(
        '<div class="main-title">'
        'ℹ️ Informasi Perpustakaan'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    ### 📚 Tentang AI Asisten Perpustakaan

    Aplikasi ini membantu pengguna:

    - Mencari koleksi buku.
    - Mendapatkan rekomendasi buku.
    - Bertanya kepada AI.
    - Mengelola data buku.
    - Mengunggah dokumen PDF.
    - Bertanya berdasarkan isi dokumen PDF.

    ### 💻 Teknologi

    - Python
    - Streamlit
    - MySQL
    - Ollama
    - Qwen 2.5 3B
    - ChromaDB
    - Retrieval-Augmented Generation (RAG)
    """)

    st.divider()

    st.write(
        f"Jumlah koleksi buku: {len(buku_list)}"
    )

    st.write(
        f"Jumlah potongan dokumen di ChromaDB: {collection.count()}"
    )

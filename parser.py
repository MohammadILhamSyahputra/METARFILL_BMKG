import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
from fill_form2 import run_test # Import fungsi dari file di atas
from auth_utils import get_db_path
import sqlite3


# PERCEPATAN: Session HTTP dipakai bersama (module-level) supaya koneksi
# TCP/TLS ke aviation.bmkg.go.id bisa di-reuse (keep-alive) antar
# pemanggilan ambil_data_metar_bmkg(), bukan buka koneksi baru dari nol
# setiap kali tombol "Ambil Data Baru" diklik dalam satu sesi aplikasi.
_bmkg_session = requests.Session()
_bmkg_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})


# =============================================================================
# AMBIL DATA METAR PER-TANGGAL (fetch + filter langsung dari web BMKG)
# =============================================================================
# CATATAN: test_input.py HANYA contoh/referensi cara ambil data per-tanggal,
# BUKAN bagian dari aplikasi ini (tidak di-import di mana pun oleh
# form_dashboard.py). Jadi logic-nya di-duplikasi & disesuaikan di sini
# sebagai fungsi mandiri milik parser.py, supaya parser.py tidak bergantung
# ke file percobaan/testing di luar alur aplikasi.
def ambil_data_metar_bmkg(tahun, bulan, tanggal):
    """
    Fetch halaman METAR BMKG untuk 1 bulan, lalu filter HANYA baris yang
    diawali tanggal spesifik (format 'DD/MM/YYYY') yang diminta.
    Mengembalikan DataFrame dengan kolom ['Waktu (UTC)', 'Data METAR'],
    atau None kalau gagal konek / tidak ada data untuk tanggal itu.
    """
    stasiun = "ward"

    # Menghilangkan angka 0 di depan bulan untuk URL (misal "02" jadi "2")
    bulan_url = str(int(bulan))
    url = f"https://aviation.bmkg.go.id/latest/metar.php?i={stasiun}&y={tahun}&m={bulan_url}"

    print(f"\nMencoba mengunduh data dari: {url}")

    try:
        # PERCEPATAN: pakai _bmkg_session (bukan requests.get() baru setiap
        # kali) supaya koneksi HTTP bisa di-reuse antar pemanggilan.
        response = _bmkg_session.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f" Gagal terhubung ke server BMKG: {e}")
        return None

    # PERCEPATAN: coba pakai parser 'lxml' (jauh lebih cepat dari
    # 'html.parser' bawaan Python) kalau library-nya sudah terpasang.
    # Kalau belum ada (ImportError), otomatis fallback ke 'html.parser'
    # seperti sebelumnya -- jadi tetap jalan walau lxml tidak diinstall.
    try:
        soup = BeautifulSoup(response.text, 'lxml')
    except Exception:
        soup = BeautifulSoup(response.text, 'html.parser')

    # PERCEPATAN: sebelumnya soup.get_text() dipanggil untuk SELURUH
    # halaman (header, menu navigasi, footer, script, dst), padahal data
    # METAR-nya sendiri ada di dalam SATU blok teks preformatted (<pre>).
    # Kalau blok <pre> ditemukan, ambil teksnya langsung -- jauh lebih
    # ringan karena tidak perlu menggabungkan teks dari seluruh node HTML
    # di halaman. Kalau strukturnya berubah dan <pre> tidak ada, tetap
    # fallback ke get_text() seluruh halaman seperti semula agar tidak
    # rusak.
    blok_pre = soup.find('pre')
    teks_halaman = blok_pre.get_text() if blok_pre is not None else soup.get_text()

    # Pecah teks menjadi baris-baris terpisah
    baris_teks = teks_halaman.split('\n')

    # Format tanggal pencarian (harus 2 digit, misal: "07/02/2026")
    tanggal_str = str(tanggal).zfill(2)
    bulan_str = str(bulan).zfill(2)
    tahun_str = str(tahun)
    target_format_tanggal = f"{tanggal_str}/{bulan_str}/{tahun_str}"

    records = []

    for baris in baris_teks:
        baris = baris.strip()

        # Cek apakah baris tersebut diawali oleh tanggal yang dicari
        if baris.startswith(target_format_tanggal):
            # Menggunakan regex untuk memisahkan Waktu (kolom pertama) dengan Data METAR (sisanya)
            # Pola ini memisah berdasarkan tab atau spasi beruntun yang memisahkan tanggal dan kode SAID
            match = re.split(r'\t|\s{2,}', baris, maxsplit=1)

            if len(match) == 2:
                waktu_utc = match[0].strip()
                data_metar = match[1].strip()
                records.append([waktu_utc, data_metar])
            elif len(match) == 1:
                # Jika pemisahnya spasi tunggal, kita coba pisahkan manual
                # Ambil 20 karakter pertama untuk Waktu ("DD/MM/YYYY HH:MM:SSZ")
                waktu_utc = baris[:20].strip()
                data_metar = baris[20:].strip()
                records.append([waktu_utc, data_metar])

    if not records:
        print(f" [Info] Tidak ditemukan baris data yang berawalan tanggal {target_format_tanggal} di halaman web.")
        return None

    # Membuat DataFrame Pandas dari baris yang berhasil difilter
    header = ["Waktu (UTC)", "Data METAR"]
    df_terfilter = pd.DataFrame(records, columns=header)

    return df_terfilter


def parse_metar(line, tahun=None, bulan=None):
    if "METAR" not in line: return None
    metar_code = line.split("METAR")[1].strip()
    parts = line.split("METAR")[1].strip().split()
    station_id = parts[0]
    timestamp = parts[1] # Contoh: 090700Z
    
    # Ambil hari dan jam
    day = timestamp[0:2]    # "09"
    hour = timestamp[2:4]   # "07"
    minute = timestamp[4:6]

    # Mapping nama field agar cocok dengan fill_form.py
    hasil = {
        "day": day,
        "hour": hour,
        "minute": minute,
        "direction": "0", "speed": "0", 
        "dir_min": "0", "dir_max": "0", 
        "visibility": "9999",
        "temp": "25", "dew_point": "20", "pressure": "1013"
    }

    now = datetime.now()
    # PENTING: sebelumnya full_date SELALU memakai now.year/now.month (bulan
    # & tahun SAAT SCRIPT DIJALANKAN). Ini salah kalau pengguna sedang minta
    # data tanggal di bulan/tahun yang berbeda lewat datepicker (mis. minta
    # data 28 Januari padahal aplikasi dibuka di bulan Juli) -- datanya akan
    # tersimpan dengan tanggal yang salah. Sekarang tahun/bulan bisa
    # di-override oleh pemanggil (proses_data_untuk_tanggal); day tetap
    # diambil dari kode METAR itu sendiri (field paling akurat untuk hari
    # observasi).
    tahun_final = tahun if tahun else now.year
    bulan_final = bulan if bulan else now.month
    hasil["full_date"] = f"{tahun_final}-{str(bulan_final).zfill(2)}-{day.zfill(2)}"
    hasil["label_date"] = f"{bulan_final}/{int(day)}/{tahun_final}"

    # PENTING: sebelumnya key 'raw_metar' TIDAK PERNAH dimasukkan ke dict
    # hasil. Akibatnya, di simpan_ke_db(), `data.get('raw_metar', 'METAR WARD ...')`
    # selalu jatuh ke nilai default placeholder karena key-nya memang tidak
    # pernah ada. Simpan baris METAR mentah (utuh, apa adanya) di sini agar
    # raw_metar yang tersimpan ke database benar-benar data asli, bukan
    # hasil parsing.
    hasil["raw_metar"] = line.strip()
    
    # Logic Parsing Anda
    angin = re.search(r'(VRB|[0-9]{3})([0-9]{2,3})(?:G([0-9]{2,3}))?KT', metar_code)
    if angin:
        hasil["direction"] = angin.group(1).replace("VRB", "0")
        hasil["speed"] = angin.group(2)
        hasil["gust"] = angin.group(3) or "0"
        
    var = re.search(r'([0-9]{3})V([0-9]{3})', metar_code)
    if var:
        hasil["dir_min"], hasil["dir_max"] = var.group(1), var.group(2)
        
    vis = re.search(r'\s([0-9]{4})\s', metar_code)
    if vis:
        vis_val = int(vis.group(1))
        # Jika kode METAR 9999, konversi ke 10000 untuk formulir
        if vis_val == 9999:
            hasil["visibility"] = "10000"
        else:
            hasil["visibility"] = str(vis_val)

    # PENTING: sebelumnya pakai re.search() yang cuma menangkap SATU layer
    # awan pertama (mis. hanya "FEW020" walau kodenya "FEW020 SCT100 BKN200"),
    # lalu disimpan sebagai 'cloud_amount'/'cloud_height' tunggal. Sekarang
    # tabel Awan mendukung sampai 3 record per observasi (lihat fill_form2.py
    # & setup_database.py), jadi di sini kita tangkap SEMUA layer awan yang
    # ada di kode METAR (maksimal 3 pertama) sebagai list 'clouds', termasuk
    # tipe awan (CB/TCU) kalau ada.
    # CATATAN: dikonfirmasi dari HTML form BMKGSatu (kolom tabel Awan
    # berjudul "TINGGI (FEET)", tooltip "Tinggi dasar awan (feet)") -- field
    # cloud_height MEMANG minta nilai feet penuh, bukan kode 3-digit METAR
    # mentah. Jadi height di sini dikonversi dari kode METAR (ratusan feet,
    # mis. "020") ke feet penuh (mis. "2000") dengan dikali 100.
    awan_matches = re.findall(r'(FEW|SCT|BKN|OVC)([0-9]{3})(CB|TCU)?', metar_code)
    hasil["clouds"] = [
        {
            "amount": amount,
            "height": str(int(height) * 100),
            "type": tipe or "",
        }
        for amount, height, tipe in awan_matches[:3]  # maksimal 3 record
    ]

    temp = re.search(r'(M?[0-9]{2})/(M?[0-9]{2})', metar_code)
    if temp:
        hasil["temp"] = temp.group(1).replace("M", "-")
        hasil["dew_point"] = temp.group(2).replace("M", "-")

    qnh = re.search(r'Q([0-9]{4}|////)', metar_code)
    if qnh:
        val = qnh.group(1)
        # Jika sensor rusak (////), kita ganti menjadi 9999
        hasil["pressure"] = "9999" if val == "////" else val
    else:
        # Jika kode Q tidak ditemukan sama sekali di METAR
        hasil["pressure"] = "9999"
        
    return hasil

def simpan_ke_db(data, raw_line=None, conn=None):
    """
    raw_line: parameter opsional berisi baris METAR mentah asli. Diterima
    agar kompatibel dengan pemanggilan simpan_ke_db(data, line) dari
    form_dashboard.py (tombol refresh). Jika tidak diberikan, akan
    memakai data['raw_metar'] yang sudah diisi oleh parse_metar().

    conn: PERCEPATAN -- opsional, koneksi sqlite3 yang SUDAH DIBUKA dan
    akan dikelola (commit & close) oleh PEMANGGIL. Dipakai oleh
    proses_data_untuk_tanggal() supaya satu batch berisi banyak baris METAR
    cukup memakai SATU koneksi, bukan buka+tutup koneksi baru untuk SETIAP
    baris (yang sebelumnya jadi bottleneck utama saat data dalam satu
    tanggal cukup banyak, mis. observasi tiap jam). Kalau conn=None (dipakai
    mandiri, mis. dari _jalankan_fetch_manual), fungsi ini tetap buka &
    tutup koneksinya sendiri seperti sebelumnya, jadi tetap kompatibel.
    """
    kelola_koneksi_sendiri = conn is None
    if kelola_koneksi_sendiri:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)

    cursor = conn.cursor()

    # Cek duplikat berdasarkan waktu dan tanggal
    cursor.execute("SELECT id_metar FROM METAR WHERE waktu_observasi = ? AND tanggal_observasi = ?", 
                   (f"{data['hour']}:{data['minute']}", data['full_date']))
    
    if cursor.fetchone():
        if kelola_koneksi_sendiri:
            conn.close()
        return "exists"

    # Prioritaskan raw_line jika diberikan langsung oleh pemanggil, jika
    # tidak, pakai data['raw_metar'] yang sudah diisi oleh parse_metar().
    # Baru kalau dua-duanya kosong, gunakan placeholder sebagai jaga-jaga.
    raw_metar_text = raw_line or data.get('raw_metar') or 'METAR WARD ...'

    # 1. Simpan ke tabel METAR
    cursor.execute("""
        INSERT INTO METAR (raw_metar, icao, tanggal_observasi, waktu_observasi) 
        VALUES (?, ?, ?, ?)""", 
        (raw_metar_text, "WARD", data['full_date'], f"{data['hour']}:{data['minute']}")
    )
    id_metar = cursor.lastrowid
    
    # 2. Simpan ke tabel Parsing_Result
    # PENTING: kolom cloud_cover / cloud_height / cloud_type SUDAH TIDAK ADA
    # lagi di tabel Parsing_Result (lihat setup_database.py) -- data awan
    # sekarang disimpan terpisah di tabel Awan (langkah 3 di bawah), karena
    # satu observasi bisa punya sampai 3 layer awan sekaligus. Sebelumnya
    # INSERT ini masih menyertakan cloud_cover/cloud_height sehingga selalu
    # gagal dengan "no such column" dan seluruh simpan_ke_db() ikut gagal
    # (termasuk data awan yang tidak pernah tersimpan).
    cursor.execute("""
        INSERT INTO Parsing_Result (
            id_metar, wind_direction, wind_speed, wind_gust, 
            wind_dir_min, wind_dir_max, visibility_prevailing, 
            temperature, dewpoint, pressure, trend
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (id_metar, data.get('direction', '0'), data.get('speed', '0'), data.get('gust', '0'), 
        data.get('dir_min', '0'), data.get('dir_max', '0'), data.get('visibility', '9999'), 
        data.get('temp', '25'), data.get('dew_point', '20'), 
        data.get('pressure', '9999'), data.get('trend', 'NOSIG'))
    )
    # Ambil ID untuk referensi tabel Awan
    id_parsing = cursor.lastrowid
    print(f"DEBUG PARSER: id_parsing yang dihasilkan: {id_parsing}")

    # 3. Simpan ke tabel Awan (mendukung sampai 3 record per observasi)
    daftar_awan = data.get('clouds', [])[:3]
    for urutan, awan in enumerate(daftar_awan, start=1):
        cursor.execute("""
            INSERT INTO Awan (id_parsing, urutan, cloud_amount, cloud_height, cloud_type) 
            VALUES (?, ?, ?, ?, ?)""",
            (id_parsing, urutan, awan.get('amount', ''), awan.get('height', ''), awan.get('type', ''))
        )
    print(f"DEBUG PARSER: {len(daftar_awan)} record awan disimpan untuk id_parsing={id_parsing}")

    # PERCEPATAN: commit & close hanya dilakukan di sini kalau koneksinya
    # dibuka sendiri oleh fungsi ini. Kalau conn dikirim oleh pemanggil
    # (batch dari proses_data_untuk_tanggal), commit-nya dilakukan SEKALI
    # oleh pemanggil setelah seluruh baris dalam batch selesai diproses --
    # jauh lebih cepat daripada commit per baris. Perilaku duplikat-check
    # tetap benar walau belum di-commit, karena baris yang baru di-INSERT
    # tapi belum di-commit di koneksi yang sama tetap terlihat oleh query
    # SELECT berikutnya di koneksi itu juga (read-your-own-writes).
    if kelola_koneksi_sendiri:
        conn.commit()
        conn.close()
    print("Data lengkap berhasil disimpan ke database!")
    return "success"

# =============================================================================
# METODE BARU: AMBIL DATA PER-TANGGAL (bukan per-bulan lagi)
# =============================================================================
def proses_data_untuk_tanggal(tahun, bulan, tanggal):
    """
    Entry point utama yang dipanggil dari form_dashboard.py (baik saat
    aplikasi pertama dibuka -- default tanggal hari ini -- maupun saat
    tombol 'Ambil Data Baru' diklik dengan tanggal dari datepicker).

    Alur:
      1. Fetch + filter baris METAR untuk SATU tanggal spesifik lewat
         ambil_data_metar_bmkg() (fungsi lokal di file ini, lihat di atas).
      2. Setiap baris hasil filter di-parse_metar() dengan tahun/bulan
         di-override sesuai tanggal yang diminta (bukan bulan berjalan).
      3. Disimpan ke DB lewat simpan_ke_db() yang sudah otomatis cek
         duplikat.

    Return: dict ringkasan supaya form_dashboard.py tinggal menampilkan
    pesan yang sesuai tanpa perlu tahu detail parsing/DB:
        {
            "total_ditemukan": jumlah baris METAR yang ketemu di web utk tanggal ini,
            "baru":            jumlah yang baru berhasil disimpan,
            "sudah_ada":       jumlah yang ternyata sudah ada di DB (duplikat),
            "gagal_parse":     jumlah baris yang gagal di-parse_metar(),
        }
    """
    ringkasan = {"total_ditemukan": 0, "baru": 0, "sudah_ada": 0, "gagal_parse": 0}

    df = ambil_data_metar_bmkg(tahun, bulan, tanggal)
    if df is None or df.empty:
        return ringkasan

    ringkasan["total_ditemukan"] = len(df)

    # PERCEPATAN: satu koneksi DB dibuka di sini untuk SELURUH baris dalam
    # batch ini (bisa belasan/puluhan baris per tanggal), lalu di-passing
    # ke simpan_ke_db() supaya tidak buka+tutup koneksi baru di setiap
    # baris. Commit juga dilakukan SEKALI di akhir (bukan per baris).
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        for _, baris in df.iterrows():
            line = baris["Data METAR"]
            data = parse_metar(line, tahun=tahun, bulan=bulan)

            if not data:
                ringkasan["gagal_parse"] += 1
                print(f"   -> WARNING: Gagal parse baris: {line}")
                continue

            status = simpan_ke_db(data, line, conn=conn)
            if status == "success":
                ringkasan["baru"] += 1
            elif status == "exists":
                ringkasan["sudah_ada"] += 1

        conn.commit()
    finally:
        conn.close()

    return ringkasan


# --- PROSES UTAMA ---
# PENTING: sebelumnya blok ini TIDAK dibungkus `if __name__ == "__main__":`,
# sehingga setiap kali file lain melakukan
# `from parser import parse_metar, simpan_ke_db` (seperti di
# form_dashboard.py), seluruh proses fetch + simpan ke database di bawah
# ini otomatis ikut berjalan sendiri saat import — di luar kendali tombol
# "Refresh" di Dashboard, dan memakai simpan_ke_db(data) versi lama
# (1 argumen) yang tidak cocok dengan pemanggilan simpan_ke_db(data, line)
# di form_dashboard.py. Dibungkus di sini agar blok ini hanya berjalan saat
# parser.py dijalankan langsung (mis. untuk testing manual), bukan saat
# di-import sebagai modul.
def _jalankan_fetch_manual():
    url = f"https://aviation.bmkg.go.id/latest/metar.php?i=ward&y={datetime.now().year}&m={datetime.now().month}"
    response = requests.get(url)
    lines = response.text.splitlines()

    # Cari baris yang mengandung 'METAR WARD'
    metar_lines = [line for line in lines if "METAR WARD" in line]

    if metar_lines:
        for line in metar_lines:
            print(f"Memproses baris: {line}")
            data = parse_metar(line)
            if data:
                # Panggil fungsi simpan_ke_db yang sudah kita buat
                simpan_ke_db(data)
        print("Semua data berhasil diproses!")
    else:
        print("Data METAR WARD tidak ditemukan di URL tersebut!")


if __name__ == "__main__":
    _jalankan_fetch_manual()
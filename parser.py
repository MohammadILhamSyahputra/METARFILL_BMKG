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


# =============================================================================
# EKSTRAK CUACA SAAT PENGAMATAN & CUACA YANG LALU DARI TEKS
# =============================================================================
# Dipisah jadi fungsi tersendiri (bukan inline di parse_metar) supaya bisa
# dipakai ulang oleh form_input.py untuk field teks bebas "Cuaca Saat
# Pengamatan" / "Cuaca yang Lalu" di GUI -- baik saat mengisi field itu dari
# data hasil parsing, MAUPUN saat membaca kembali isi field itu (yang bisa
# saja sudah diedit manual oleh observer) sebelum dikirim ke fill_form2.py.
# Dengan begini logikanya SATU tempat saja, tidak dobel antara parser.py dan
# form_input.py.
_WX_INTENSITY_RE = r'(?P<intensity>[-+]|VC)?'
_WX_DESCRIPTOR_RE = r'(?P<descriptor>MI|PR|BC|DR|BL|SH|TS|FZ)?'
_WX_PHENOMENA_RE = r'(?P<phenomena>(?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+)?'
_WX_PATTERN = re.compile(r'^(?P<re>RE)?' + _WX_INTENSITY_RE + _WX_DESCRIPTOR_RE + _WX_PHENOMENA_RE + r'$')

# Kode fenomena presipitasi vs. obscuration vs. lainnya -- dipakai untuk
# memetakan ke radio group 'radio-precipitation' / 'radio-obscuration' /
# 'radio-other' di fill_form2.py.
_KODE_PRESIPITASI = {"DZ", "RA", "SN", "SG", "IC", "PL", "GR", "GS", "UP"}
_KODE_OBSCURATION = {"BR", "FG", "FU", "VA", "DU", "SA", "HZ", "PY"}
_KODE_LAINNYA = {"PO", "SQ", "FC", "SS", "DS"}

# Token yang jelas bukan kode cuaca, dilewati supaya tidak sia-sia dicoba
# dicocokkan (atau -- lebih penting -- supaya tidak salah ke-parse).
_WX_TOKEN_ABAIKAN = {"NOSIG", "CAVOK", "AUTO", "NIL", "COR"}


def ekstrak_cuaca(teks):
    """
    Format kode cuaca METAR standar WMO: [RE](intensitas)(deskriptor)(fenomena):
      "TS"      -> deskriptor TS (thunderstorm), tanpa fenomena presipitasi
      "+TSRA"   -> intensitas +, deskriptor TS, fenomena RA (hujan)
      "-TSRA"   -> intensitas -, deskriptor TS, fenomena RA
      "RERA"    -> cuaca YANG LALU (prefix RE) fenomena RA
      "RETS"    -> cuaca YANG LALU (prefix RE) deskriptor TS

    Menerima teks bebas (dipecah per-spasi) -- bisa berupa potongan kode
    METAR mentah, atau isi field teks bebas di GUI. Mengembalikan dict:
      {
        "weather_intensity": None|"", "-", "+", "VC"
        "weather_descriptor": None atau salah satu MI/PR/BC/DR/BL/SH/TS/FZ
        "weather_precipitation": None atau salah satu kode presipitasi
        "weather_obscuration": None atau salah satu kode obscuration
        "weather_other": None atau salah satu kode lainnya (PO/SQ/FC/SS/DS)
        "recent_weather": None atau kode cuaca yang lalu (tanpa prefix RE)
      }
    "" (string kosong, BUKAN None) pada weather_intensity berarti intensitas
    Moderate -- tetap dianggap pilihan valid oleh isi_radio_group() di
    fill_form2.py, jangan disamakan dengan None (None = grup dilewati sama
    sekali / tidak ada cuaca).
    """
    hasil_cuaca = {
        "weather_intensity": None,
        "weather_descriptor": None,
        "weather_precipitation": None,
        "weather_obscuration": None,
        "weather_other": None,
        "recent_weather": None,
    }

    cuaca_saat_ini = None   # token cuaca saat pengamatan pertama yang ketemu
    cuaca_lalu = None       # token cuaca yang lalu (RE...) pertama yang ketemu

    for tok in (teks or "").split():
        tok = tok.strip().upper()
        if not tok or tok in _WX_TOKEN_ABAIKAN:
            continue
        m = _WX_PATTERN.match(tok)
        if not m:
            continue
        deskriptor = m.group("descriptor")
        fenomena = m.group("phenomena")
        # Kalau deskriptor & fenomena dua-duanya kosong, token ini bukan
        # kode cuaca sungguhan (mis. token kosong / hanya kebetulan cocok).
        if not deskriptor and not fenomena:
            continue

        if m.group("re"):
            if cuaca_lalu is None:
                cuaca_lalu = {"descriptor": deskriptor or "", "phenomena": fenomena or ""}
        else:
            if cuaca_saat_ini is None:
                cuaca_saat_ini = {
                    "intensity": m.group("intensity") or "",
                    "descriptor": deskriptor or "",
                    "phenomena": fenomena or "",
                }

    if cuaca_saat_ini:
        hasil_cuaca["weather_intensity"] = cuaca_saat_ini["intensity"]
        if cuaca_saat_ini["descriptor"]:
            hasil_cuaca["weather_descriptor"] = cuaca_saat_ini["descriptor"]
        if cuaca_saat_ini["phenomena"]:
            # Kalau fenomenanya gabungan (mis. "RASN"), ambil kode 2 huruf
            # pertama saja -- form hanya punya satu radio per kategori.
            kode2 = cuaca_saat_ini["phenomena"][:2]
            if kode2 in _KODE_PRESIPITASI:
                hasil_cuaca["weather_precipitation"] = kode2
            elif kode2 in _KODE_OBSCURATION:
                hasil_cuaca["weather_obscuration"] = kode2
            elif kode2 in _KODE_LAINNYA:
                hasil_cuaca["weather_other"] = kode2

    if cuaca_lalu:
        # CATATAN/ASUMSI: dropdown #recent-w-1 di fill_form2.py diasumsikan
        # memakai kode singkat TANPA prefix "RE" (mis. "RA", "TS", "SHRA"),
        # karena kita belum punya HTML asli formulirnya untuk memastikan
        # opsi value-nya persis apa. Kalau ternyata value dropdownnya beda
        # (mis. pakai "RERA" utuh, atau kode WMO yang berbeda), sesuaikan
        # baris ini.
        hasil_cuaca["recent_weather"] = (cuaca_lalu["descriptor"] or "") + (cuaca_lalu["phenomena"] or "")

    return hasil_cuaca


def parse_metar(line, tahun=None, bulan=None):
    if "METAR" not in line: return None
    metar_code = line.split("METAR")[1].strip()

    # PERBAIKAN BUG UTAMA: sebelumnya station_id & timestamp diambil dari
    # parts[0]/parts[1] secara membabi-buta. Ini SALAH untuk baris koreksi
    # yang formatnya "METAR COR WARD 080430Z ..." -- kata "COR" ikut
    # terhitung sebagai parts[0], sehingga parts[1] yang seharusnya
    # timestamp ("080430Z") malah kebagian "WARD" (station_id). Akibatnya
    # day = "WA", dan int(day) di full_date/label_date meledak dengan
    # "invalid literal for int() with base 10: 'WA'" -- persis error yang
    # dilaporkan, dan HANYA muncul pada tanggal yang punya baris koreksi
    # (CCA/CCB/CCC).
    #
    # Sekarang dipakai regex yang secara eksplisit mengizinkan (opsional)
    # token "COR" di depan station_id, jadi posisi station_id & timestamp
    # selalu benar tidak peduli baris itu koreksi atau bukan.
    header_match = re.match(r'(?:COR\s+)?([A-Z0-9]{4})\s+(\d{6})Z', metar_code)
    if not header_match:
        print(f"   -> WARNING: Header METAR tidak dikenali, baris dilewati: {line.strip()}")
        return None

    station_id = header_match.group(1)
    timestamp = header_match.group(2) + "Z"  # Contoh: 090700Z

    # Ambil hari dan jam
    day = timestamp[0:2]    # "09"
    hour = timestamp[2:4]   # "07"
    minute = timestamp[4:6]

    # Flag status laporan: COR (koreksi), AUTO (observasi otomatis tanpa
    # observer), NIL (tidak ada laporan/data). Dicek sebagai kata utuh
    # supaya tidak salah kena token lain yang kebetulan mengandung huruf
    # yang sama.
    is_cor = bool(re.match(r'COR\s', metar_code))
    is_auto = bool(re.search(r'\bAUTO\b', metar_code))
    is_nil = bool(re.search(r'\bNIL\b', metar_code))

    # Mapping nama field agar cocok dengan fill_form.py
    hasil = {
        "day": day,
        "hour": hour,
        "minute": minute,
        "direction": "0", "speed": "0", 
        "dir_min": "0", "dir_max": "0", 
        "visibility": "9999",
        "temp": "25", "dew_point": "20", "pressure": "1013",
        "is_cor": is_cor,
        "is_auto": is_auto,
        "is_nil": is_nil,
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

    # PERBAIKAN: sebelumnya visibility dicari dengan `\s([0-9]{4})\s` yang
    # MENGHARUSKAN persis 4 digit. Ini melewatkan dua kasus nyata:
    #   1. "CAVOK" (visibility >= 10km, tidak ada awan signifikan di bawah
    #      5000ft, tidak ada cuaca signifikan) -- sebelumnya tidak dikenali
    #      sama sekali, visibility jatuh ke default "9999" yang salah.
    #   2. Visibility di bawah 1000 meter kadang ditulis 3 digit tanpa
    #      leading zero (mis. "500" alih-alih "0500"), lihat baris jam
    #      07:00Z tanggal 04/12 di data yang dilaporkan -- sebelumnya token
    #      3-digit ini tidak pernah ketemu oleh regex 4-digit.
    # Sekarang dicari per-token: token "CAVOK" ditangani eksplisit, lalu
    # token pertama yang murni 3-4 digit dianggap visibility. Token lain di
    # baris METAR (arah angin+KT, awan macam "FEW020", suhu "28/24", QNH
    # "Q1013") semuanya punya huruf/tanda baca yang menempel, jadi tidak
    # akan ketiban match ini.
    for tok in metar_code.split():
        if tok == "CAVOK":
            hasil["visibility"] = "10000"
            break
        if re.fullmatch(r'[0-9]{3,4}', tok):
            vis_val = int(tok)
            # Jika kode METAR 9999, konversi ke 10000 untuk formulir
            hasil["visibility"] = "10000" if vis_val == 9999 else str(vis_val)
            break

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

    # CUACA SAAT PENGAMATAN & CUACA YANG LALU (BARU -- sebelumnya sama
    # sekali tidak diparse). Logikanya ada di ekstrak_cuaca() di atas
    # supaya bisa dipakai ulang oleh form_input.py.
    hasil.update(ekstrak_cuaca(metar_code))

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

    # Cek apakah sudah ada baris utk waktu+tanggal yang sama.
    cursor.execute("SELECT id_metar FROM METAR WHERE waktu_observasi = ? AND tanggal_observasi = ?", 
                   (f"{data['hour']}:{data['minute']}", data['full_date']))
    baris_lama = cursor.fetchone()

    # Prioritaskan raw_line jika diberikan langsung oleh pemanggil, jika
    # tidak, pakai data['raw_metar'] yang sudah diisi oleh parse_metar().
    # Baru kalau dua-duanya kosong, gunakan placeholder sebagai jaga-jaga.
    raw_metar_text = raw_line or data.get('raw_metar') or 'METAR WARD ...'

    # PERBAIKAN: sebelumnya kalau sudah ada baris utk waktu+tanggal yang
    # sama, baris baru langsung DISKIP ("exists") -- artinya kalau BMKG
    # mengirim koreksi (CCA/CCB/CCC) utk jam yang sama, koreksinya TIDAK
    # PERNAH tersimpan, dan yang tersimpan tetap laporan AUTO/awal yang
    # salah. Karena proses_data_untuk_tanggal() memproses baris berurutan
    # dari atas ke bawah sesuai urutan tampil di web BMKG (AUTO -> CCA ->
    # CCB -> CCC), dan permintaan-nya adalah "ambil yang paling
    # akhir/bawah", maka sekarang baris yang sudah ada di-UPDATE dengan
    # data terbaru (bukan di-skip), sehingga versi terakhir yang menang.
    if baris_lama:
        id_metar = baris_lama[0]

        cursor.execute(
            "UPDATE METAR SET raw_metar = ? WHERE id_metar = ?",
            (raw_metar_text, id_metar)
        )

        cursor.execute("""
            UPDATE Parsing_Result SET
                wind_direction = ?, wind_speed = ?, wind_gust = ?,
                wind_dir_min = ?, wind_dir_max = ?, visibility_prevailing = ?,
                temperature = ?, dewpoint = ?, pressure = ?, trend = ?
            WHERE id_metar = ?""",
            (data.get('direction', '0'), data.get('speed', '0'), data.get('gust', '0'),
             data.get('dir_min', '0'), data.get('dir_max', '0'), data.get('visibility', '9999'),
             data.get('temp', '25'), data.get('dew_point', '20'),
             data.get('pressure', '9999'), data.get('trend', 'NOSIG'), id_metar)
        )

        cursor.execute("SELECT id_parsing FROM Parsing_Result WHERE id_metar = ?", (id_metar,))
        row = cursor.fetchone()
        id_parsing = row[0] if row else None

        if id_parsing is not None:
            # Ganti seluruh record Awan lama dengan yang baru (paling
            # sederhana & aman ketimbang mencoba mencocokkan urutan lama
            # vs baru satu-satu, karena jumlah layer awan bisa berubah
            # antar versi koreksi).
            cursor.execute("DELETE FROM Awan WHERE id_parsing = ?", (id_parsing,))
            daftar_awan = data.get('clouds', [])[:3]
            for urutan, awan in enumerate(daftar_awan, start=1):
                cursor.execute("""
                    INSERT INTO Awan (id_parsing, urutan, cloud_amount, cloud_height, cloud_type) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (id_parsing, urutan, awan.get('amount', ''), awan.get('height', ''), awan.get('type', ''))
                )
            print(f"DEBUG PARSER: {len(daftar_awan)} record awan diperbarui untuk id_parsing={id_parsing}")

        if kelola_koneksi_sendiri:
            conn.commit()
            conn.close()
        print(f"Data untuk {data['full_date']} {data['hour']}:{data['minute']} DIPERBARUI (koreksi/CCx) di database!")
        return "updated"

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
    ringkasan = {"total_ditemukan": 0, "baru": 0, "sudah_ada": 0, "gagal_parse": 0, "diperbarui": 0}

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
            elif status == "updated":
                ringkasan["diperbarui"] += 1
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
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
from fill_form2 import run_test 
from auth_utils import get_db_path
import sqlite3


_bmkg_session = requests.Session()
_bmkg_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})


def ambil_data_metar_bmkg(tahun, bulan, tanggal):
    stasiun = "ward"

    bulan_url = str(int(bulan))
    url = f"https://aviation.bmkg.go.id/latest/metar.php?i={stasiun}&y={tahun}&m={bulan_url}"

    print(f"\nMencoba mengunduh data dari: {url}")

    try:
        response = _bmkg_session.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f" Gagal terhubung ke server BMKG: {e}")
        return None

    try:
        soup = BeautifulSoup(response.text, 'lxml')
    except Exception:
        soup = BeautifulSoup(response.text, 'html.parser')

    blok_pre = soup.find('pre')
    teks_halaman = blok_pre.get_text() if blok_pre is not None else soup.get_text()

    baris_teks = teks_halaman.split('\n')

    tanggal_str = str(tanggal).zfill(2)
    bulan_str = str(bulan).zfill(2)
    tahun_str = str(tahun)
    target_format_tanggal = f"{tanggal_str}/{bulan_str}/{tahun_str}"

    records = []

    for baris in baris_teks:
        baris = baris.strip()

        # Cek apakah baris tersebut diawali oleh tanggal yang dicari
        if baris.startswith(target_format_tanggal):
            match = re.split(r'\t|\s{2,}', baris, maxsplit=1)

            if len(match) == 2:
                waktu_utc = match[0].strip()
                data_metar = match[1].strip()
                records.append([waktu_utc, data_metar])
            elif len(match) == 1:
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


_WX_INTENSITY_RE = r'(?P<intensity>[-+]|VC)?'
_WX_DESCRIPTOR_RE = r'(?P<descriptor>MI|PR|BC|DR|BL|SH|TS|FZ)?'
_WX_PHENOMENA_RE = r'(?P<phenomena>(?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+)?'
_WX_PATTERN = re.compile(r'^(?P<re>RE)?' + _WX_INTENSITY_RE + _WX_DESCRIPTOR_RE + _WX_PHENOMENA_RE + r'$')
_KODE_PRESIPITASI = {"DZ", "RA", "SN", "SG", "IC", "PL", "GR", "GS", "UP"}
_KODE_OBSCURATION = {"BR", "FG", "FU", "VA", "DU", "SA", "HZ", "PY"}
_KODE_LAINNYA = {"PO", "SQ", "FC", "SS", "DS"}
_WX_TOKEN_ABAIKAN = {"NOSIG", "CAVOK", "AUTO", "NIL", "COR"}


def ekstrak_cuaca(teks):
    hasil_cuaca = {
        "weather_intensity": None,
        "weather_descriptor": None,
        "weather_precipitation": None,
        "weather_obscuration": None,
        "weather_other": None,
        "recent_weather": None,
    }

    cuaca_saat_ini = None   
    cuaca_lalu = None      

    for tok in (teks or "").split():
        tok = tok.strip().upper()
        if not tok or tok in _WX_TOKEN_ABAIKAN:
            continue
        m = _WX_PATTERN.match(tok)
        if not m:
            continue
        deskriptor = m.group("descriptor")
        fenomena = m.group("phenomena")
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
            kode2 = cuaca_saat_ini["phenomena"][:2]
            if kode2 in _KODE_PRESIPITASI:
                hasil_cuaca["weather_precipitation"] = kode2
            elif kode2 in _KODE_OBSCURATION:
                hasil_cuaca["weather_obscuration"] = kode2
            elif kode2 in _KODE_LAINNYA:
                hasil_cuaca["weather_other"] = kode2

    if cuaca_lalu:
        hasil_cuaca["recent_weather"] = (cuaca_lalu["descriptor"] or "") + (cuaca_lalu["phenomena"] or "")

    return hasil_cuaca


def parse_metar(line, tahun=None, bulan=None):
    if "METAR" not in line: return None
    metar_code = line.split("METAR")[1].strip()

    header_match = re.match(r'(?:COR\s+)?([A-Z0-9]{4})\s+(\d{6})Z', metar_code)
    if not header_match:
        print(f"   -> WARNING: Header METAR tidak dikenali, baris dilewati: {line.strip()}")
        return None

    station_id = header_match.group(1)
    timestamp = header_match.group(2) + "Z"  # Contoh: 090700Z

    day = timestamp[0:2]    # "09"
    hour = timestamp[2:4]   # "07"
    minute = timestamp[4:6]

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
    tahun_final = tahun if tahun else now.year
    bulan_final = bulan if bulan else now.month
    hasil["full_date"] = f"{tahun_final}-{str(bulan_final).zfill(2)}-{day.zfill(2)}"
    hasil["label_date"] = f"{bulan_final}/{int(day)}/{tahun_final}"

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

    for tok in metar_code.split():
        if tok == "CAVOK":
            hasil["visibility"] = "10000"
            break
        if re.fullmatch(r'[0-9]{3,4}', tok):
            vis_val = int(tok)
            # Jika kode METAR 9999, konversi ke 10000 untuk formulir
            hasil["visibility"] = "10000" if vis_val == 9999 else str(vis_val)
            break

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

    hasil.update(ekstrak_cuaca(metar_code))

    return hasil

def simpan_ke_db(data, raw_line=None, conn=None):
    kelola_koneksi_sendiri = conn is None
    if kelola_koneksi_sendiri:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)

    cursor = conn.cursor()

    cursor.execute("SELECT id_metar FROM METAR WHERE waktu_observasi = ? AND tanggal_observasi = ?", 
                   (f"{data['hour']}:{data['minute']}", data['full_date']))
    baris_lama = cursor.fetchone()

    raw_metar_text = raw_line or data.get('raw_metar') or 'METAR WARD ...'

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

    if kelola_koneksi_sendiri:
        conn.commit()
        conn.close()
    print("Data lengkap berhasil disimpan ke database!")
    return "success"

def proses_data_untuk_tanggal(tahun, bulan, tanggal):

    ringkasan = {"total_ditemukan": 0, "baru": 0, "sudah_ada": 0, "gagal_parse": 0, "diperbarui": 0}

    df = ambil_data_metar_bmkg(tahun, bulan, tanggal)
    if df is None or df.empty:
        return ringkasan

    ringkasan["total_ditemukan"] = len(df)

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
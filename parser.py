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

    header = ["Waktu (UTC)", "Data METAR"]
    df_terfilter = pd.DataFrame(records, columns=header)

    return df_terfilter


# ==============================================================================
# SUMBER DATA ALTERNATIF: web-aviation.bmkg.go.id/web/metar_speci.php
# ==============================================================================
# Halaman ini pakai proteksi CSRF token (khas Laravel), jadi alurnya:
#   1) GET halaman metar_speci.php -> ambil cookie sesi + nilai _token dari
#      hidden input <input type="hidden" name="_token" value="...">
#   2) POST ke URL yang sama dengan form-data: stasiun, from, to, metar, speci,
#      _token -> server membalas HTML yang berisi <table id="table_id"> berisi
#      baris-baris data METAR/SPECI.

_WEB_AVIATION_URL = "https://web-aviation.bmkg.go.id/web/metar_speci.php"

_web_aviation_session = requests.Session()
_web_aviation_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
})


def _ambil_token_web_aviation():
    """Membuka halaman metar_speci.php untuk mendapatkan cookie sesi baru
    dan nilai CSRF token (_token) yang wajib disertakan saat POST."""
    response = _web_aviation_session.get(_WEB_AVIATION_URL, timeout=30)
    response.raise_for_status()

    try:
        soup = BeautifulSoup(response.text, 'lxml')
    except Exception:
        soup = BeautifulSoup(response.text, 'html.parser')

    token_input = soup.find('input', attrs={'name': '_token'})
    if token_input is not None and token_input.get('value'):
        return token_input['value']

    # Fallback: sebagian halaman Laravel menaruh token di meta tag
    meta_token = soup.find('meta', attrs={'name': 'csrf-token'})
    if meta_token is not None and meta_token.get('content'):
        return meta_token['content']

    # Fallback terakhir: cari lewat regex mentah di HTML
    match = re.search(r'name=["\']_token["\']\s+value=["\']([^"\']+)["\']', response.text)
    if match:
        return match.group(1)

    raise RuntimeError("Tidak dapat menemukan CSRF token (_token) di halaman metar_speci.php")


def ambil_data_metar_web_aviation(tahun, bulan, tanggal, stasiun="WARD"):
    """Mengambil data METAR dari web-aviation.bmkg.go.id/web/metar_speci.php
    untuk satu hari penuh (00:00 s.d. 23:59 UTC) pada stasiun tertentu.
    Mengembalikan DataFrame dengan kolom yang sama seperti
    ambil_data_metar_bmkg agar bisa dipakai oleh proses_data_untuk_tanggal
    tanpa perubahan lebih lanjut."""

    tanggal_str = str(tanggal).zfill(2)
    bulan_str = str(bulan).zfill(2)
    tahun_str = str(tahun)

    dari_waktu = f"{tahun_str}-{bulan_str}-{tanggal_str}T00:00"
    sampai_waktu = f"{tahun_str}-{bulan_str}-{tanggal_str}T23:59"

    print(f"\nMencoba mengunduh data dari: {_WEB_AVIATION_URL} "
          f"(stasiun={stasiun}, {dari_waktu} s/d {sampai_waktu})")

    try:
        token = _ambil_token_web_aviation()

        payload = {
            "stasiun": stasiun,
            "from": dari_waktu,
            "to": sampai_waktu,
            "metar": "SA",
            "speci": "SP",
            "_token": token,
        }

        response = _web_aviation_session.post(_WEB_AVIATION_URL, data=payload, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f" Gagal terhubung ke server web-aviation BMKG: {e}")
        return None

    try:
        soup = BeautifulSoup(response.text, 'lxml')
    except Exception:
        soup = BeautifulSoup(response.text, 'html.parser')

    tabel = soup.find('table', id='table_id')
    if tabel is None:
        print(" [Info] Tabel data (table_id) tidak ditemukan di respons web-aviation.")
        return None

    tbody = tabel.find('tbody')
    if tbody is None:
        print(" [Info] Tidak ada tbody pada tabel hasil web-aviation.")
        return None

    records = []
    for baris in tbody.find_all('tr'):
        kolom = baris.find_all('td')
        if len(kolom) < 4:
            continue

        data_metar = kolom[0].get_text(strip=True)
        waktu_observasi = kolom[3].get_text(strip=True)

        # Hanya proses baris METAR; baris SPECI sengaja dilewati di sini
        # supaya tidak ikut terhitung sebagai "gagal_parse" oleh parse_metar
        # (yang memang hanya mengenali baris berisi kata "METAR").
        if "METAR" not in data_metar:
            continue

        records.append([waktu_observasi, data_metar])

    if not records:
        print(f" [Info] Tidak ditemukan data METAR untuk stasiun {stasiun} "
              f"tanggal {tanggal_str}/{bulan_str}/{tahun_str} di web-aviation.")
        return None

    header = ["Waktu (UTC)", "Data METAR"]
    df_terfilter = pd.DataFrame(records, columns=header)

    return df_terfilter


# Sumber data yang tersedia untuk dipilih dari dashboard.
SUMBER_AVIATION_LAMA = "aviation"        # aviation.bmkg.go.id
SUMBER_WEB_AVIATION = "web_aviation"     # web-aviation.bmkg.go.id


def ambil_data_metar(tahun, bulan, tanggal, sumber=SUMBER_AVIATION_LAMA, stasiun="WARD"):
    """Dispatcher: mengambil data METAR dari sumber yang dipilih."""
    if sumber == SUMBER_WEB_AVIATION:
        return ambil_data_metar_web_aviation(tahun, bulan, tanggal, stasiun=stasiun)
    return ambil_data_metar_bmkg(tahun, bulan, tanggal)


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
        "is_vrb": False,
    }

    now = datetime.now()
    #tahun_final = tahun if tahun else now.year
    #bulan_final = bulan if bulan else now.month

    #hasil["full_date"] = f"{tahun_final}-{str(bulan_final).zfill(2)}-{day.zfill(2)}"
    #hasil["label_date"] = f"{bulan_final}/{int(day)}/{tahun_final}"

    tahun_final = int(tahun) if tahun is not None else now.year
    bulan_final = int(bulan) if bulan is not None else now.month

    hasil["full_date"] = f"{tahun_final}-{str(bulan_final).zfill(2)}-{str(day).zfill(2)}"
    hasil["label_date"] = f"{bulan_final}/{int(day)}/{tahun_final}"

    hasil["raw_metar"] = line.strip()
    
    angin = re.search(r'(VRB|[0-9]{3})([0-9]{2,3})(?:G([0-9]{2,3}))?KT', metar_code)
    if angin:
        arah_angin_raw = angin.group(1)
        hasil["direction"] = arah_angin_raw.replace("VRB", "0")
        hasil["speed"] = angin.group(2)
        hasil["gust"] = angin.group(3) or "0"
        if arah_angin_raw == "VRB":
            hasil["is_vrb"] = True

    var = re.search(r'([0-9]{3})V([0-9]{3})', metar_code)
    if var:
        hasil["dir_min"], hasil["dir_max"] = var.group(1), var.group(2)
        hasil["is_vrb"] = True

    for tok in metar_code.split():
        if tok == "CAVOK":
            hasil["visibility"] = "10000"
            break
        if re.fullmatch(r'[0-9]{3,4}', tok):
            vis_val = int(tok)
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
        hasil["pressure"] = "9999" if val == "////" else val
    else:
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
    id_parsing = cursor.lastrowid
    print(f"DEBUG PARSER: id_parsing yang dihasilkan: {id_parsing}")

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

def proses_data_untuk_tanggal(tahun, bulan, tanggal, sumber=SUMBER_AVIATION_LAMA, stasiun="WARD"):

    ringkasan = {"total_ditemukan": 0, "baru": 0, "sudah_ada": 0, "gagal_parse": 0, "diperbarui": 0}

    df = ambil_data_metar(tahun, bulan, tanggal, sumber=sumber, stasiun=stasiun)
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

    metar_lines = [line for line in lines if "METAR WARD" in line]

    if metar_lines:
        for line in metar_lines:
            print(f"Memproses baris: {line}")
            data = parse_metar(line)
            if data:
                simpan_ke_db(data)
        print("Semua data berhasil diproses!")
    else:
        print("Data METAR WARD tidak ditemukan di URL tersebut!")


if __name__ == "__main__":
    _jalankan_fetch_manual()
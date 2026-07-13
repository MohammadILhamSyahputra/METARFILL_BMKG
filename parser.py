import requests
from datetime import datetime
import re
from fill_form2 import run_test # Import fungsi dari file di atas
from auth_utils import get_db_path
import sqlite3

def parse_metar(line):
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
        "visibility": "9999", "cloud_amount": "FEW", 
        "cloud_height": "2000", "temp": "25", "dew_point": "20", "pressure": "1013"
    }

    now = datetime.now()
    hasil["full_date"] = f"{now.year}-{str(now.month).zfill(2)}-{day.zfill(2)}"
    hasil["label_date"] = f"{now.month}/{int(day)}/{now.year}"

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
        
    awan = re.search(r'(FEW|SCT|BKN|OVC)([0-9]{3})', metar_code)
    if awan:
        hasil["cloud_amount"] = awan.group(1)
        hasil["cloud_height"] = str(int(awan.group(2)) * 100)
        
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

def simpan_ke_db(data, raw_line=None):
    """
    raw_line: parameter opsional berisi baris METAR mentah asli. Diterima
    agar kompatibel dengan pemanggilan simpan_ke_db(data, line) dari
    form_dashboard.py (tombol refresh). Jika tidak diberikan, akan
    memakai data['raw_metar'] yang sudah diisi oleh parse_metar().
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Cek duplikat berdasarkan waktu dan tanggal
    cursor.execute("SELECT id_metar FROM METAR WHERE waktu_observasi = ? AND tanggal_observasi = ?", 
                   (f"{data['hour']}:{data['minute']}", data['full_date']))
    
    if cursor.fetchone():
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
    
    # 2. Simpan ke tabel Parsing_Result dengan data lengkap
    cursor.execute("""
        INSERT INTO Parsing_Result (
            id_metar, wind_direction, wind_speed, wind_gust, 
            wind_dir_min, wind_dir_max, visibility_prevailing, 
            cloud_cover, cloud_height, temperature, dewpoint, 
            pressure, trend
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            id_metar, 
            data.get('direction', '0'), 
            data.get('speed', '0'), 
            data.get('gust', '0'), 
            data.get('dir_min', '0'), 
            data.get('dir_max', '0'), 
            data.get('visibility', '9999'), 
            data.get('cloud_amount', 'FEW'),
            data.get('cloud_height', '2000'), 
            data.get('temp', '25'), 
            data.get('dew_point', '20'), 
            data.get('pressure', '9999'),
            data.get('trend', 'NOSIG')
        )
    )
    
    conn.commit()
    conn.close()
    print("Data lengkap berhasil disimpan ke database!")
    return "success"

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
import requests
from datetime import datetime
import re
from fill_form2 import run_test # Import fungsi dari file di atas

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

# --- PROSES UTAMA ---
url = f"https://aviation.bmkg.go.id/latest/metar.php?i=ward&y={datetime.now().year}&m={datetime.now().month}"
response = requests.get(url)
lines = response.text.splitlines()

# Cari baris yang mengandung 'METAR WARD'
metar_lines = [line for line in lines if "METAR WARD" in line]

if metar_lines:
    # Ambil baris TERAKHIR (biasanya yang paling baru)
    latest_metar = metar_lines[-1]
    print(f"Membaca baris METAR: {latest_metar}")
    
    data = parse_metar(latest_metar)
    if data:
        print(f"Data diparsing: {data}")
        run_test(data)
else:
    print("Data METAR WARD tidak ditemukan di URL tersebut!")
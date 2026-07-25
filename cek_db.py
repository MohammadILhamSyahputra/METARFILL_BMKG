import sqlite3
from auth_utils import get_db_path

def cek_database():
    db_path = get_db_path()
    print(f"Menghubungkan ke database: {db_path}\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Cek total baris di masing-masing tabel
    tabel_list = ["METAR", "Parsing_Result", "Awan", "AutoFill_History"]
    print("--- TOTAL DATA PER TABEL ---")
    for tabel in tabel_list:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabel}")
            total = cursor.fetchone()[0]
            print(f"Tabel {tabel}: {total} baris")
        except sqlite3.OperationalError:
            print(f"Tabel {tabel}: Belum dibuat/ditemukan")
    
    print("\n--- RENTANG TANGGAL DI TABEL METAR ---")
    try:
        # Cek tanggal paling tua dan paling baru
        cursor.execute("SELECT MIN(tanggal_observasi), MAX(tanggal_observasi) FROM METAR")
        min_date, max_date = cursor.fetchone()
        print(f"Data tertua : {min_date}")
        print(f"Data terbaru: {max_date}")
    except Exception as e:
        print(f"Gagal mengecek tanggal: {e}")
        
    # 2. Contoh cek spesifik (seperti id_metar 823 yang Anda tanyakan sebelumnya)
    print("\n--- CONTOH CEK DETAIL ID_METAR 823 ---")
    cursor.execute("""
        SELECT m.id_metar, m.tanggal_observasi, p.id_parsing 
        FROM METAR m 
        LEFT JOIN Parsing_Result p ON m.id_metar = p.id_metar 
        WHERE m.id_metar = 823
    """)
    result = cursor.fetchone()
    if result:
        print(f"Ditemukan -> ID Metar: {result[0]}, Tanggal: {result[1]}, ID Parsing: {result[2]}")
    else:
        print("Data dengan ID Metar 823 tidak ditemukan (mungkin sudah terhapus oleh filter 30 hari).")

    conn.close()

if __name__ == "__main__":
    cek_database()
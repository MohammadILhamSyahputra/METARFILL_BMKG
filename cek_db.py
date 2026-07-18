import sqlite3
from auth_utils import get_db_path

def cek_tabel_awan():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    # Menghitung jumlah data di tabel Awan
    cursor.execute("SELECT COUNT(*) FROM Awan")
    jumlah = cursor.fetchone()[0]
    print(f"Jumlah baris di tabel Awan: {jumlah}")
    
    # Jika ingin melihat isi datanya, Anda bisa mengambil beberapa baris
    if jumlah > 0:
        cursor.execute("SELECT * FROM Awan LIMIT 5")
        rows = cursor.fetchall()
        print("Contoh data 5 baris pertama:")
        for row in rows:
            print(row)
            
    conn.close()

if __name__ == "__main__":
    cek_tabel_awan()
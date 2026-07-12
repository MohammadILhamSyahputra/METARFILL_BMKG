import sqlite3
from auth_utils import get_db_path

conn = sqlite3.connect(get_db_path())
cursor = conn.cursor()
cursor.execute("SELECT * FROM METAR")
data = cursor.fetchall()
print(f"Jumlah baris di tabel METAR: {len(data)}")
conn.close()
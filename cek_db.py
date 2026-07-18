import sqlite3
from auth_utils import get_db_path

conn = sqlite3.connect(get_db_path())
cursor = conn.cursor()
cursor.execute("SELECT id_parsing FROM Parsing_Result WHERE id_metar = 823")
result = cursor.fetchone()
print(f"DEBUG DB: id_parsing di database untuk id_metar 823 adalah: {result}")
conn.close()
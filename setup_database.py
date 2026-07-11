import sqlite3
from auth_utils import hash_password, get_db_path


def create_database():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Menginisialisasi database SQLite: '{db_path}' berdasarkan ERD...")

    # TABEL Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        id_user INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # TABEL METAR
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS METAR (
        id_metar INTEGER PRIMARY KEY AUTOINCREMENT,
        id_parsing INTEGER, -- Menghubungkan ke tabel Parsing Result
        id_user INTEGER,    -- Menghubungkan ke pembuat/inputer data
        raw_metar TEXT NOT NULL,
        icao TEXT NOT NULL,
        tanggal_observasi TEXT NOT NULL, -- Format standar: YYYY-MM-DD
        waktu_observasi TEXT NOT NULL,   -- Format standar: HH:MM (UTC)
        FOREIGN KEY (id_user) REFERENCES Users(id_user) ON DELETE SET NULL,
        FOREIGN KEY (id_parsing) REFERENCES Parsing_Result(id_parsing) ON DELETE SET NULL
    )
    """)

    # TABEL Parsing Result
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Parsing_Result (
        id_parsing INTEGER PRIMARY KEY AUTOINCREMENT,
        id_metar INTEGER,   -- Relasi balik ke METAR master

        wind_direction TEXT,               -- input#winds-direction
        wind_speed TEXT,                   -- input#wind_speed
        wind_gust TEXT,                    -- input#wind_gust
        wind_dir_min TEXT,                 -- input#winds-wd-dn
        wind_dir_max TEXT,                 -- input#winds-wd-dx

        visibility_prevailing TEXT,        -- input#input-prevailing
        visibility_minimum TEXT,           -- input#input-minimum

        cloud_cover TEXT,                  -- select#clouds-jumlah (FEW, SCT, BKN, OVC)
        cloud_height TEXT,                 -- input#cloud_height
        cloud_type TEXT,                   -- select#select-type (CB, TCU)
        vertical_vis TEXT,                 -- input#clouds-vertical-vis

        weather_intensity TEXT,            -- radio-intensity ("", "-", "+", "VC")
        weather_descriptor TEXT,           -- radio-descriptor ("TS", "SH", "MI", dll)

        temperature TEXT,                  -- input#v-air-temp
        dewpoint TEXT,                     -- input#v-dew-point
        pressure TEXT,                     -- input#v-presure

        trend TEXT,                        -- select[data-v-1010a25b]#input-type (Trend)

        FOREIGN KEY (id_metar) REFERENCES METAR(id_metar) ON DELETE CASCADE
    )
    """)

    # TABEL AutoFill History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS AutoFill_History (
        id_history INTEGER PRIMARY KEY AUTOINCREMENT,
        id_user INTEGER,
        id_metar INTEGER,
        waktu_send TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL, -- Contoh: "SUKSES", "GAGAL", "PENDING"
        FOREIGN KEY (id_user) REFERENCES Users(id_user) ON DELETE SET NULL,
        FOREIGN KEY (id_metar) REFERENCES METAR(id_metar) ON DELETE SET NULL
    )
    """)

    # User admin default -> password di-hash, JANGAN disimpan plain text
    cursor.execute(
        "INSERT OR IGNORE INTO Users (nama, password, role) VALUES (?, ?, ?)",
        ("admin", hash_password("admin123"), "Admin"),
    )

    conn.commit()
    conn.close()
    print("Sukses! Seluruh struktur tabel dan relasi ERD berhasil dibuat.")


if __name__ == "__main__":
    create_database()
# auth_utils.py
"""
Modul utilitas bersama untuk seluruh aplikasi METARFill.

Berisi:
- hash_password()  -> hashing password dengan SHA-256 (jangan simpan password
  dalam bentuk plain text di database).
- get_db_path()    -> path absolut ke file database, supaya aplikasi tetap
  bisa menemukan database_metar.db walaupun dijalankan dari direktori kerja
  (cwd) yang berbeda-beda.
"""

import os
import hashlib


def hash_password(password: str) -> str:
    """Hash password menggunakan SHA-256 sebelum disimpan/dibandingkan di database."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_db_path() -> str:
    """Selalu mengarah ke database_metar.db yang sejajar dengan file-file .py
    aplikasi ini, apapun direktori kerja saat aplikasi dijalankan."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "database_metar.db")
import sys
import os
import sqlite3

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFrame, QSpacerItem, QSizePolicy,
                             QMessageBox, QCompleter)  # Tambah QCompleter di sini
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt

from auth_utils import hash_password, get_db_path


class LoginPage(QWidget):
    def __init__(self):
        super().__init__()

        # Konfigurasi Dasar Jendela
        self.setWindowTitle("METARFill - Login Page")
        self.setFixedSize(900, 600)
        self.setObjectName("main_window")

        # Background warna abu-abu muda/putih sesuai gambar
        # Ditambahkan styling QMessageBox agar warna teks notifikasi popup menjadi hitam tegas
        self.setStyleSheet("""
            #main_window {
                background-color: #f5f9f9;
            }
            QLabel {
                color: black;
                font-family: 'Segoe UI', Arial;
            }
            QMessageBox QLabel {
                color: black;
            }
            QMessageBox QPushButton {
                color: black;
                background-color: #E0E0E0;
                padding: 5px 15px;
                border-radius: 4px;
            }
        """)

        # Layout Utama (Horizontal: Sisi Kiri & Sisi Kanan)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)

        # ================= SISI KIRI (BRANDING) =================
        self.left_container = QVBoxLayout()

        # 1. Header BMKG (Top Left)
        self.header_bmkg_layout = QHBoxLayout()
        
        self.logo_label = QLabel()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir,"logo-bmkg.png")
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(50, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText("[Logo]")
            self.logo_label.setStyleSheet("font-weight: bold; color: #0070C0;")

        self.text_header_layout = QVBoxLayout()
        self.label_main_title = QLabel("BADAN METEOROLOGI, KLIMATOLOGI, DAN GEOFISIKA")
        self.label_main_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.label_main_title.setStyleSheet("color: #0070C0;")
        
        self.label_sub_title = QLabel("STASIUN METEOROLOGI KELAS III DHOHO KEDIRI")
        self.label_sub_title.setFont(QFont("Segoe UI", 8))
        self.label_sub_title.setStyleSheet("color: #555555;")
        
        self.text_header_layout.addWidget(self.label_main_title)
        self.text_header_layout.addWidget(self.label_sub_title)
        self.text_header_layout.addStretch()

        self.header_bmkg_layout.addWidget(self.logo_label)
        self.header_bmkg_layout.addLayout(self.text_header_layout)
        self.left_container.addLayout(self.header_bmkg_layout)

        self.left_container.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 2. Gambar Ilustrasi Utama (Center Left)
        self.illustration_label = QLabel()
        ill_path = os.path.join(current_dir, "assets", "login_illustration.png")
        if os.path.exists(ill_path):
            pixmap_ill = QPixmap(ill_path).scaled(380, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.illustration_label.setPixmap(pixmap_ill)
        else:
            self.illustration_label.setStyleSheet("background-color: #E0EBF5; border-radius: 10px;")
            self.illustration_label.setFixedSize(380, 250)
            self.illustration_label.setText("METARFill Automation System")
            self.illustration_label.setAlignment(Qt.AlignCenter)
            self.illustration_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
            
        self.illustration_label.setAlignment(Qt.AlignCenter)
        self.left_container.addWidget(self.illustration_label)
        
        self.left_container.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # ================= SISI KANAN (FORM LOGIN CARD) =================
        self.right_frame = QFrame()
        self.right_frame.setFixedWidth(380)
        self.right_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
            }
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 10px;
                font-size: 11pt;
                color: black;
                background-color: #FAFAFA;
            }
            QLineEdit:focus {
                border: 1px solid #0070C0;
                background-color: white;
            }
            QPushButton {
                background-color: #0070C0;
                color: white;
                border-radius: 6px;
                padding: 12px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        """)

        self.form_layout = QVBoxLayout(self.right_frame)
        self.form_layout.setContentsMargins(30, 40, 30, 40)
        self.form_layout.setSpacing(15)

        # Welcome Text
        self.label_welcome = QLabel("Selamat Datang")
        self.label_welcome.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.label_welcome.setStyleSheet("color: black;")
        
        self.label_instruction = QLabel("Silakan login menggunakan akun personil stasiun.")
        self.label_instruction.setFont(QFont("Segoe UI", 10))
        self.label_instruction.setStyleSheet("color: #777777;")
        
        self.form_layout.addWidget(self.label_welcome)
        self.form_layout.addWidget(self.label_instruction)
        self.form_layout.addSpacerItem(QSpacerItem(20, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Input Username
        self.form_layout.addWidget(QLabel("Nama Lengkap"))
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Masukkan Nama Lengkap Anda")
        self.form_layout.addWidget(self.input_username)

        # =========================================================
        # PROSES PEMASANGAN AUTOCOMPLETE TEXT (AMBIL DARI DATABASE)
        # =========================================================
        daftar_nama = self.ambil_daftar_nama_dari_db()
        completer = QCompleter(daftar_nama, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.input_username.setCompleter(completer)
        # =========================================================

        # Input Password
        self.form_layout.addWidget(QLabel("Password"))
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Masukkan Password")
        self.input_password.setEchoMode(QLineEdit.Password)
        self.form_layout.addWidget(self.input_password)

        self.form_layout.addSpacerItem(QSpacerItem(20, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Sign In Button
        self.btn_login = QPushButton("Sign In")
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self.proses_login)
        self.form_layout.addWidget(self.btn_login)

        # Susun ke layout utama horizontal
        self.main_layout.addLayout(self.left_container, stretch=1)
        self.main_layout.addWidget(self.right_frame, stretch=0)

    def ambil_daftar_nama_dari_db(self):
        """Mengambil daftar nama personil dari SQLite untuk Autocomplete"""
        nama_list = []
        try:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT nama FROM Users")
            rows = cursor.fetchall()
            for row in rows:
                if row[0]:
                    nama_list.append(row[0])
            conn.close()
        except Exception as e:
            print(f"Gagal memuat data autocomplete: {e}")
        return nama_list

    def proses_login(self):
        username = self.input_username.text().strip()
        password = self.input_password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Peringatan", "Nama lengkap dan password wajib diisi!")
            return

        try:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id_user, nama, role
                FROM Users
                WHERE nama = ? AND password = ?
                """,
                (username, hash_password(password)),
            )
            user = cursor.fetchone()
            conn.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Kesalahan Database", f"Gagal terhubung ke database:\n{e}")
            return

        if user is None:
            QMessageBox.warning(self, "Login Gagal", "Username atau password salah!")
            return

        id_user, nama, role = user
        user_data = {"id_user": id_user, "nama": nama, "role": role}
        self.buka_halaman_sesuai_role(user_data)

    def buka_halaman_sesuai_role(self, user_data):
        role = (user_data.get("role") or "").strip().lower()

        if role == "admin":
            from admin_page import AdminApp
            self.next_window = AdminApp(user_data=user_data)
        else:
            from form_dashboard import DashboardApp
            self.next_window = DashboardApp(user_data=user_data)

        self.next_window.show()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginPage()
    window.show()
    sys.exit(app.exec())
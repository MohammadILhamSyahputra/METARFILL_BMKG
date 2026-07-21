import sys
import os
import sqlite3

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFrame, QSpacerItem, QSizePolicy,
                             QMessageBox, QCompleter)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt

from auth_utils import hash_password, get_db_path


class LoginPage(QWidget):
    def __init__(self):
        super().__init__()

        # Konfigurasi Dasar Jendela
        self.setWindowTitle("METARFill - Futuristic Login")
        self.setFixedSize(960, 640)
        self.setObjectName("main_window")

        # Gaya Global & Background Utama Putih Bersih
        self.setStyleSheet("""
            #main_window {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #222222;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMessageBox {
                background-color: #FFFFFF;
            }
            QMessageBox QLabel {
                color: #222222;
            }
            QMessageBox QPushButton {
                color: #222222;
                background-color: #F0F0F0;
                padding: 6px 18px;
                border-radius: 6px;
                border: none;
            }
            QLineEdit {
                border: none;
                border-bottom: 2px solid #D0D8E8;
                border-radius: 0px;
                padding: 10px 4px;
                font-size: 11pt;
                color: #222222;
                background-color: transparent;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #0070C0;
            }
            QPushButton {
                background-color: #0070C0;
                color: white;
                border-radius: 8px;
                padding: 14px 20px;
                font-size: 11pt;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)

        # Layout Utama (Horizontal: Sisi Kiri & Sisi Kanan)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(50, 40, 50, 40)
        self.main_layout.setSpacing(40)

        self.left_container = QVBoxLayout()
        self.left_container.setSpacing(10)

        # 1. Header BMKG (Top Left)
        self.header_bmkg_layout = QHBoxLayout()
        self.header_bmkg_layout.setSpacing(15)

        self.logo_label = QLabel()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "logo-bmkg.png")

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(55, 66, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText("[Logo]")
            self.logo_label.setStyleSheet("font-weight: bold; color: #0070C0; font-size: 16px;")

        self.text_header_layout = QVBoxLayout()
        self.label_main_title = QLabel("BADAN METEOROLOGI, KLIMATOLOGI,\nDAN GEOFISIKA")
        self.label_main_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.label_main_title.setStyleSheet("color: #0070C0; line-height: 1.2;")
        
        self.label_sub_title = QLabel("STASIUN METEOROLOGI KELAS III DHOHO KEDIRI")
        self.label_sub_title.setFont(QFont("Segoe UI", 8))
        self.label_sub_title.setStyleSheet("color: #666666;")
        
        self.text_header_layout.addWidget(self.label_main_title)
        self.text_header_layout.addWidget(self.label_sub_title)
        self.text_header_layout.setSpacing(2)

        self.header_bmkg_layout.addWidget(self.logo_label)
        self.header_bmkg_layout.addLayout(self.text_header_layout)
        self.header_bmkg_layout.addStretch()

        self.left_container.addLayout(self.header_bmkg_layout)
        self.left_container.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # 2. Gambar Ilustrasi Utama (Center Left)
        self.illustration_label = QLabel()
        ill_path = os.path.join(current_dir, "METARFill_Logo.png")
        if os.path.exists(ill_path):
            pixmap_ill = QPixmap(ill_path).scaled(420, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.illustration_label.setPixmap(pixmap_ill)
        else:
            self.illustration_label.setStyleSheet("background-color: #F4F7FC; border-radius: 16px;")
            self.illustration_label.setFixedSize(420, 280)
            self.illustration_label.setText("METARFill Automation System")
            self.illustration_label.setAlignment(Qt.AlignCenter)
            self.illustration_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            self.illustration_label.setStyleSheet("color: #0070C0;")
            
        self.illustration_label.setAlignment(Qt.AlignCenter)
        self.left_container.addWidget(self.illustration_label)
        
        self.left_container.addStretch()

        self.right_container = QVBoxLayout()
        self.right_container.addStretch()  

        self.login_card = QFrame()
        self.login_card.setFixedWidth(400)
        self.login_card.setStyleSheet("""
            QFrame {
                background-color: #F0F5FA;
                border-radius: 16px;
            }
        """)

        self.form_layout = QVBoxLayout(self.login_card)
        self.form_layout.setContentsMargins(35, 40, 35, 40)
        self.form_layout.setSpacing(24)

        # Welcome Text (Di dalam kontainer)
        self.welcome_layout = QVBoxLayout()
        self.welcome_layout.setSpacing(6)
        
        self.label_welcome = QLabel("Selamat Datang")
        self.label_welcome.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.label_welcome.setStyleSheet("color: #222222;")
        
        self.label_instruction = QLabel("Silakan masuk untuk melanjutkan sistem automasi.")
        self.label_instruction.setFont(QFont("Segoe UI", 10))
        self.label_instruction.setStyleSheet("color: #666666;")
        
        self.welcome_layout.addWidget(self.label_welcome)
        self.welcome_layout.addWidget(self.label_instruction)
        self.form_layout.addLayout(self.welcome_layout)

        # Input Nama Lengkap
        self.username_layout = QVBoxLayout()
        self.username_layout.setSpacing(6)
        
        self.lbl_user = QLabel("Nama Lengkap")
        self.lbl_user.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.lbl_user.setStyleSheet("color: #444444;")
        
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Masukkan Nama Lengkap Anda")
        
        self.username_layout.addWidget(self.lbl_user)
        self.username_layout.addWidget(self.input_username)
        self.form_layout.addLayout(self.username_layout)

        # Autocomplete Proses
        daftar_nama = self.ambil_daftar_nama_dari_db()
        completer = QCompleter(daftar_nama, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.input_username.setCompleter(completer)

        # Input Password
        self.password_layout = QVBoxLayout()
        self.password_layout.setSpacing(6)
        
        self.lbl_pass = QLabel("Password")
        self.lbl_pass.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.lbl_pass.setStyleSheet("color: #444444;")
        
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Masukkan Password")
        self.input_password.setEchoMode(QLineEdit.Password)
        
        self.password_layout.addWidget(self.lbl_pass)
        self.password_layout.addWidget(self.input_password)
        self.form_layout.addLayout(self.password_layout)

        self.form_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Tombol Sign In
        self.btn_login = QPushButton("Sign In")
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self.proses_login)
        self.form_layout.addWidget(self.btn_login)
        self.right_container.addWidget(self.login_card)
        self.right_container.addStretch()  
        self.main_layout.addLayout(self.left_container, stretch=1)
        self.main_layout.addLayout(self.right_container, stretch=0)

    def ambil_daftar_nama_dari_db(self):
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
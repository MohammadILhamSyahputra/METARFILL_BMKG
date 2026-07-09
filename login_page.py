import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QFrame, QSpacerItem, QSizePolicy)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt

class LoginPage(QWidget):
    def __init__(self):
        super().__init__()

        # Konfigurasi Dasar Jendela
        self.setWindowTitle("METARFill - Login Page")
        self.setFixedSize(900, 600)
        self.setObjectName("main_window")
        
        # Background warna abu-abu muda/putih sesuai gambar
        self.setStyleSheet("""
            #main_window {
                background-color: #f5f9f9;
            }
            QLabel {
                color: black;
                font-family: 'Segoe UI', Arial;
            }
        """)

        # Layout Utama (Horizontal: Sisi Kiri & Sisi Kanan)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)

        # ================= SISI KIRI (BRANDING) =================
        self.left_container = QVBoxLayout()

        # 1. Header BMKG (Top Left)
        self.header_layout = QHBoxLayout()
        self.logo_bmkg = QLabel()
        # Ganti 'bmkg_logo.png' dengan path file logomu
        # self.logo_bmkg.setPixmap(QPixmap("bmkg_logo.png").scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_bmkg.setText("LOGO\nBMKG") # Placeholder jika gambar tidak ada
        self.logo_bmkg.setFixedSize(60, 60)

        self.title_label = QLabel("STASIUN METEOROLOGI KELAS III\nDHOHO KEDIRI")
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.header_layout.addWidget(self.logo_bmkg)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch() # Mendorong ke kiri
        
        # 2. METARFill Logo (Center)
        self.brand_layout = QVBoxLayout()
        self.brand_layout.setAlignment(Qt.AlignCenter)
        
        self.logo_metar = QLabel()
        # self.logo_metar.setPixmap(QPixmap("metarfill_logo.png").scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_metar.setText("[ LOGO METARFill ]") # Placeholder
        self.logo_metar.setAlignment(Qt.AlignCenter)
        self.logo_metar.setFixedSize(300, 200)
        self.logo_metar.setStyleSheet("font-size: 20px; color: #1e6aa5; border: 1px dashed gray;")

        self.tagline = QLabel("Sistem Otomatisasi Pengisian METAR\nTerintegrasi")
        self.tagline.setAlignment(Qt.AlignCenter)
        self.tagline.setFont(QFont("Arial", 10, QFont.Bold))

        self.brand_layout.addWidget(self.logo_metar)
        self.brand_layout.addWidget(self.tagline)

        self.left_container.addLayout(self.header_layout)
        self.left_container.addStretch()
        self.left_container.addLayout(self.brand_layout)
        self.left_container.addStretch()

        # ================= SISI KANAN (KOTAK LOGIN) =================
        self.login_card = QFrame()
        self.login_card.setFixedSize(350, 450)
        self.login_card.setStyleSheet("""
            QFrame {
                background-color: #d3d3d3;
                border-radius: 10px;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #a0a0a0;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
                color: black;
            }
            QPushButton {
                background-color: #0000cd;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00008b;
            }
            QLabel {
                background: transparent;
            }
        """)

        card_layout = QVBoxLayout(self.login_card)
        card_layout.setContentsMargins(30, 40, 30, 40)
        card_layout.setSpacing(15)

        # Widget di dalam Card
        login_title = QLabel("Login")
        login_title.setFont(QFont("Arial", 22, QFont.Bold))

        user_label = QLabel("Username")
        user_label.setFont(QFont("Arial", 12))
        self.user_input = QLineEdit()

        pass_label = QLabel("Password")
        pass_label.setFont(QFont("Arial", 12))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)

        self.login_btn = QPushButton("LOGIN")

        # Menambah widget ke layout card
        card_layout.addWidget(login_title)
        card_layout.addSpacing(10)
        card_layout.addWidget(user_label)
        card_layout.addWidget(self.user_input)
        card_layout.addWidget(pass_label)
        card_layout.addWidget(self.pass_input)
        card_layout.addSpacing(20)
        card_layout.addWidget(self.login_btn)
        card_layout.addStretch()

        # Gabungkan semua ke main layout
        self.main_layout.addLayout(self.left_container, 60)
        self.main_layout.addWidget(self.login_card, 40)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginPage()
    window.show()
    sys.exit(app.exec())
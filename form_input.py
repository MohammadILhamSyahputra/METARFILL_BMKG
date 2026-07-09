import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFrame, QGridLayout, QSpacerItem, 
    QSizePolicy, QButtonGroup
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QCheckBox, QComboBox

class MetarApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stasiun Meteorologi Kelas III Dhoho Kediri")
        self.resize(1000, 650)
        self.setStyleSheet("background-color: #F0F4F8; font-family: 'Segoe UI', Arial, sans-serif;")

        # Main Layout: Top Header + Bottom Content
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

       # 1. HEADER SECTION
        header = QWidget()
        header.setObjectName("Header")
        header.setMinimumHeight(80)
        # Menambahkan aturan agar semua QLabel di dalam header tidak memiliki background (transparan)
        header.setStyleSheet("""
            QWidget#Header {
                background-color: #0070C0;
            }
            QLabel {
                color: white;
                background-color: transparent; /* Menghilangkan background putih */
                border: none;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # Logo BMKG menggunakan QPixmap (.png)
        logo_title_layout = QHBoxLayout()
        logo_label = QLabel()
        
        # Memuat gambar png dan mengatur ukurannya (misal: tinggi 50px, lebar menyesuaikan)
        pixmap_logo = QPixmap("logo-bmkg.png")
        if not pixmap_logo.isNull():
            logo_label.setPixmap(pixmap_logo.scaledToHeight(50, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_label.setText("🔵") # Fallback jika gambar tidak ditemukan
        
        title_text = QLabel("STASIUN METEOROLOGI KELAS III\nDHOHO KEDIRI")
        title_text.setFont(QFont("Arial", 11, QFont.Bold))
        
        logo_title_layout.addWidget(logo_label)
        logo_title_layout.addWidget(title_text)
        header_layout.addLayout(logo_title_layout)

        header_layout.addStretch()

        # User Profile menggunakan QPixmap (.png)
        user_layout = QHBoxLayout()
        user_name = QLabel("Zenita Endriani")
        user_name.setFont(QFont("Arial", 11, QFont.Bold))
        
        user_icon = QLabel()
        # Memuat gambar png ikon user (misal: nama filenya user-icon.png)
        pixmap_user = QPixmap("user-icon.png") 
        if not pixmap_user.isNull():
            user_icon.setPixmap(pixmap_user.scaledToHeight(35, Qt.TransformationMode.SmoothTransformation))
        else:
            user_icon.setText("👤") # Fallback jika gambar tidak ditemukan
            user_icon.setStyleSheet("font-size: 20px; color: white; background-color: transparent;")
            
        user_layout.addWidget(user_name)
        user_layout.addWidget(user_icon)
        header_layout.addLayout(user_layout)

        main_layout.addWidget(header)

        # 2. BODY SECTION (Sidebar + Content Form)
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # --- SIDEBAR ---
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                border-right: 1px solid #E0E0E0;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #000000;
                text-align: left;
                padding-left: 20px;
                font-size: 14px;
                font-weight: bold;
                height: 45px;
            }
            QPushButton:hover {
                background-color: #E8F0FE;
            }
            /* Efek ketika menu dipilih / diklik */
            QPushButton:checked {
                background-color: #005691;
                color: white;
            }
            QPushButton#LogoutBtn {
                color: #000000;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)

        # Button Group agar sistemnya seperti Radio Button (hanya 1 yang aktif)
        self.menu_group = QButtonGroup(self)
        self.menu_group.setExclusive(True)

        menu_items = ["Dashboard", "Riwayat METAR", "Perbarui Sesi Login"]
        for item in menu_items:
            btn = QPushButton(item)
            btn.setCheckable(True)
            self.menu_group.addButton(btn)
            sidebar_layout.addWidget(btn)
            
            # Default aktifkan menu pertama (Dashboard)
            if item == "Dashboard":
                btn.setChecked(True)

        sidebar_layout.addStretch()

        logout_btn = QPushButton("LOGOUT")
        logout_btn.setObjectName("LogoutBtn")
        sidebar_layout.addWidget(logout_btn)

        body_layout.addWidget(sidebar)

        # --- CONTENT FORM ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 20, 30, 20)

        form_title = QLabel("Form Input & Preview")
        form_title.setFont(QFont("Arial", 16, QFont.Bold))
        form_title.setStyleSheet("color: #000000; margin-bottom: 10px;")
        content_layout.addWidget(form_title)

        # White Box Card Area
        card_widget = QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
            }
            QLabel {
                color: #000000;
                font-weight: bold;
                font-size: 12px;
            }
            QLabel#SectionTitle {
                color: blue;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit {
                border: 1px solid #A0A0A0;
                border-radius: 8px;
                padding: 4px;
                background-color: white;
                color: black;
                font-size: 13px;
            }
            QCheckBox{
                background: transparent;
            }

            QCheckBox::indicator{
                width:18px;
                height:18px;
                border:1px solid #A0A0A0;
                border-radius:4px;
                background:white;
            }

            QCheckBox::indicator:hover{
                border:1px solid #A0A0A0;
            }

            QCheckBox::indicator:checked{
                background:#0078D7;
                border:1px solid #A0A0A0;
                image:url(check.png);
            }
             
        """)
        card_layout = QVBoxLayout(card_widget)
        card_layout.setContentsMargins(25, 25, 25, 25)

        # METAR Preview Box
        metar_title = QLabel("METAR")
        metar_title.setObjectName("SectionTitle")
        card_layout.addWidget(metar_title)

        self.input_metar = QLineEdit()
        self.input_metar.setPlaceholderText("METAR WARD ...")
        self.input_metar.setMinimumHeight(40)
        card_layout.addWidget(self.input_metar)
        card_layout.addSpacing(15)

        # Grid Layout untuk membagi kolom Angin, Kualitas Udara, dll
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)

        # --- KOLOM KIRI (ANGIN & VISIBILITY) ---
        left_box = QVBoxLayout()
        
        # Section Angin
        angin_frame = QFrame()
        angin_frame.setStyleSheet("transparent; border: 1px solid #D0D0D0; padding: 10px;")
        angin_layout = QGridLayout(angin_frame)
        
        angin_title = QLabel("ANGIN")
        angin_title.setObjectName("SectionTitle")
        angin_layout.addWidget(angin_title, 0, 0, 1, 2)
        
        angin_layout.addWidget(QLabel("Arah Angin"), 1, 0)
        arah_layout = QHBoxLayout()
        arah_layout.setSpacing(8)

        self.input_arah_angin = QLineEdit()
        arah_layout.addWidget(self.input_arah_angin)

        # Label VRB
        vrb_label = QLabel("VRB")
        arah_layout.addWidget(vrb_label)

        # Checkbox tanpa teks
        self.checkbox_vrb_arah = QCheckBox("")
        arah_layout.addWidget(self.checkbox_vrb_arah)

        # Agar posisi tetap rapi
        arah_layout.addStretch()

        angin_layout.addLayout(arah_layout, 1, 1)

        angin_layout.addWidget(QLabel("Kecepatan Angin"), 2, 0)
        self.input_kecepatan_angin = QLineEdit()
        angin_layout.addWidget(self.input_kecepatan_angin, 2, 1)

        angin_layout.addWidget(QLabel("Variasi Angin"), 3, 0, 1, 2)
        
        var_layout = QHBoxLayout()
        var_layout.addWidget(QLabel("Arah min"))
        self.input_arah_min = QLineEdit()
        var_layout.addWidget(self.input_arah_min)
        var_layout.addWidget(QLabel("Arah max"))
        self.input_arah_max = QLineEdit()
        var_layout.addWidget(self.input_arah_max)
        angin_layout.addLayout(var_layout, 4, 0, 1, 2)
        
        left_box.addWidget(angin_frame)
        left_box.addSpacing(10)

        # Section Visibility
        vis_frame = QFrame()
        vis_frame.setStyleSheet("transparent; border: 1px solid #D0D0D0; padding: 10px;")
        vis_layout = QGridLayout(vis_frame)
        
        vis_title = QLabel("VISIBILITY")
        vis_title.setObjectName("SectionTitle")
        vis_layout.addWidget(vis_title, 0, 0, 1, 2)
        
        vis_layout.addWidget(QLabel("Prevailing (m)"), 1, 0)

        prevailing_layout = QHBoxLayout()
        prevailing_layout.setSpacing(8)

        # Input Prevailing

        self.input_prevailing = QLineEdit()
        prevailing_layout.addWidget(self.input_prevailing)

        # Label NDV
        ndv_label = QLabel("NDV")
        prevailing_layout.addWidget(ndv_label)

        # Checkbox tanpa teks
        self.checkbox_ndv = QCheckBox("")
        prevailing_layout.addWidget(self.checkbox_ndv)

        # Agar posisi tetap rapi
        prevailing_layout.addStretch()

        vis_layout.addLayout(prevailing_layout, 1, 1)

        vis_layout.addLayout(prevailing_layout, 1, 1)
        vis_layout.addWidget(QLabel("Minimum"), 2, 0)
        self.input_minimum = QLineEdit()
        vis_layout.addWidget(self.input_minimum, 2, 1)
        vis_layout.addWidget(QLabel("Min Vis Direction"), 3, 0)
        self.input_min_vis_direction = QLineEdit()
        vis_layout.addWidget(self.input_min_vis_direction, 3, 1)

        left_box.addWidget(vis_frame)
        grid_layout.addLayout(left_box, 0, 0)

        # --- KOLOM KANAN (WAKTU, AWAN, KUALITAS UDARA) ---
        right_box = QVBoxLayout()

        # Section Waktu
        waktu_layout = QHBoxLayout()
        waktu_title = QLabel("WAKTU")
        waktu_title.setObjectName("SectionTitle")
        waktu_layout.addWidget(waktu_title)
        waktu_layout.addStretch()

        waktu_input_layout = QHBoxLayout()
        waktu_input_layout.setSpacing(5) # Jarak antar input kecil saja

        self.input_jam = QLineEdit()
        self.input_jam.setPlaceholderText("HH")
        self.input_jam.setFixedWidth(45) # Ukuran pas untuk 2 angka jam
        self.input_jam.setAlignment(Qt.AlignmentFlag.AlignCenter)

        titik_dua = QLabel(":")
        titik_dua.setStyleSheet("color: black; font-weight: bold; background: transparent;")

        self.input_menit = QLineEdit()
        self.input_menit.setPlaceholderText("MM")
        self.input_menit.setFixedWidth(45) # Ukuran pas untuk 2 angka menit
        self.input_menit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        waktu_input_layout.addWidget(self.input_jam)
        waktu_input_layout.addWidget(titik_dua)
        waktu_input_layout.addWidget(self.input_menit)

        waktu_layout.addLayout(waktu_input_layout)
        
        right_box.addLayout(waktu_layout)
        right_box.addSpacing(10)

        # Section Awan
        awan_frame = QFrame()
        awan_frame.setStyleSheet("transparent; border: 1px solid #D0D0D0; padding: 10px;")
        awan_layout = QGridLayout()
        awan_title = QLabel("AWAN")
        awan_title.setObjectName("SectionTitle")
        awan_layout.addWidget(awan_title, 0, 0, 1, 2)   

        awan_layout.addWidget(QLabel("Jumlah"), 1, 0)
        self.input_jumlah_awan = QLineEdit()
        awan_layout.addWidget(self.input_jumlah_awan, 1, 1)

        awan_layout.addWidget(QLabel("Tinggi (FEET)"), 2, 0)
        self.input_tinggi_awan = QLineEdit()
        awan_layout.addWidget(self.input_tinggi_awan, 2, 1)
        
        awan_frame.setLayout(awan_layout)
        right_box.addWidget(awan_frame)
        right_box.addSpacing(10)

        # Section Kualitas Udara
        ku_frame = QFrame()
        ku_frame.setStyleSheet("transparent; border: 1px solid #D0D0D0; padding: 10px;")
        ku_layout = QGridLayout()
        ku_title = QLabel("KUALITAS UDARA")
        ku_title.setObjectName("SectionTitle")
        ku_layout.addWidget(ku_title, 0, 0, 1, 2)

        ku_layout.addWidget(QLabel("Temperature"), 1, 0)
        self.input_temp = QLineEdit()
        ku_layout.addWidget(self.input_temp, 1, 1)

        ku_layout.addWidget(QLabel("Titik Embun"), 2, 0)
        self.input_embun = QLineEdit()
        ku_layout.addWidget(self.input_embun, 2, 1)
        
        ku_frame.setLayout(ku_layout)
        right_box.addWidget(ku_frame)
        grid_layout.addLayout(right_box, 0, 1)

        card_layout.addLayout(grid_layout)
        card_layout.addStretch()

        # --- TOMBOL BATAL & KIRIM DATA ---
        action_btn_layout = QHBoxLayout()
        action_btn_layout.addStretch()

        batal_btn = QPushButton("BATAL")
        batal_btn.setStyleSheet("""
            QPushButton {
                background-color: red;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 40px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #D32F2F; }
        """)
        
        kirim_btn = QPushButton("KIRIM DATA")
        kirim_btn.setStyleSheet("""
            QPushButton {
                background-color: blue;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 40px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #0000CD; }
        """)

        action_btn_layout.addWidget(batal_btn)
        action_btn_layout.addSpacing(20)
        action_btn_layout.addWidget(kirim_btn)
        
        card_layout.addLayout(action_btn_layout)
        content_layout.addWidget(card_widget)
        body_layout.addWidget(content_container)

        main_layout.addLayout(body_layout)

        # Set Central Widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MetarApp()
    window.show()
    sys.exit(app.exec())
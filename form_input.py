import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFrame, QGridLayout, QSpacerItem, 
    QSizePolicy, QButtonGroup, QCheckBox, QComboBox, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QFont, QIcon

from session_worker import SessionUpdateWorker

class MetarApp(QMainWindow):
    def __init__(self, data_metar=None, user_data=None):
        super().__init__()
        self.data_metar = data_metar
        self.user_data = user_data or {"id_user": None, "nama": "Zenita Endriani", "role": "Observer"}
        self.setWindowTitle("Stasiun Meteorologi Kelas III Dhoho Kediri")
        self.resize(1100, 700) # Sedikit diperlebar agar proporsi grid seimbang
        self.setStyleSheet("background-color: #F0F4F8; font-family: 'Segoe UI', Arial, sans-serif;")

        # Main Layout: Top Header + Bottom Content
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================
        # 1. HEADER SECTION
        # ==========================================
        header = QWidget()
        header.setObjectName("Header")
        header.setMinimumHeight(80)
        header.setStyleSheet("""
            QWidget#Header {
                background-color: #0070C0;
            }
            QLabel {
                color: white;
                background-color: transparent;
                border: none;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # Logo BMKG menggunakan QPixmap
        logo_title_layout = QHBoxLayout()
        logo_label = QLabel()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Coba muat file png dengan path absolut
        pixmap_logo = QPixmap(os.path.join(current_dir, "logo-bmkg.png"))
        
        # Jika png gagal, otomatis coba muat file webp sebagai cadangan
        if pixmap_logo.isNull():
            pixmap_logo = QPixmap(os.path.join(current_dir, "logo-bmkg.webp"))

        if not pixmap_logo.isNull():
            logo_label.setPixmap(pixmap_logo.scaledToHeight(50, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_label.setText("🔵")       
        title_text = QLabel("STASIUN METEOROLOGI KELAS III\nDHOHO KEDIRI")
        title_text.setFont(QFont("Arial", 11, QFont.Bold))
        
        logo_title_layout.addWidget(logo_label)
        logo_title_layout.addWidget(title_text)
        header_layout.addLayout(logo_title_layout)

        header_layout.addStretch()

        # User Profile menggunakan QPixmap
        user_layout = QHBoxLayout()
        user_name = QLabel("Zenita Endriani")
        user_name.setFont(QFont("Arial", 11, QFont.Bold))

        # User Profile
        user_layout = QHBoxLayout()
        user_name = QLabel(self.user_data.get("nama", "Observer"))
        user_name.setFont(QFont("Arial", 11, QFont.Bold))
        
        user_icon = QLabel()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        pixmap_user = QPixmap(os.path.join(current_dir, "user-icon.png"))
        if not pixmap_user.isNull():
            user_icon.setPixmap(pixmap_user.scaledToHeight(35, Qt.TransformationMode.SmoothTransformation))
        else:
            user_icon.setText("👤")
            user_icon.setStyleSheet("font-size: 20px; color: white; background-color: transparent;")
            
        user_layout.addWidget(user_name)
        user_layout.addWidget(user_icon)
        header_layout.addLayout(user_layout)

        main_layout.addWidget(header)

        # ==========================================
        # 2. BODY SECTION (Sidebar + Content Form)
        # ==========================================
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

        self.menu_group = QButtonGroup(self)
        self.menu_group.setExclusive(True)

        menu_items = ["Dashboard", "Riwayat METAR", "Perbarui Sesi Login"]
        for item in menu_items:
            btn = QPushButton(item)
            btn.setCheckable(True)
            self.menu_group.addButton(btn)
            sidebar_layout.addWidget(btn)
            if item == "Dashboard":
                btn.setChecked(False) 
            if item == "Perbarui Sesi Login":
                btn.clicked.connect(self.perbarui_sesi_login)

        sidebar_layout.addStretch()

        logout_btn = QPushButton("LOGOUT")
        logout_btn.setObjectName("LogoutBtn")
        sidebar_layout.addWidget(logout_btn)
        body_layout.addWidget(sidebar)

        # --- CONTENT CONTAINER (Form Title & Scroll Area) ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 20, 30, 20)

        form_title = QLabel("Form Input & Preview")
        form_title.setFont(QFont("Arial", 16, QFont.Bold))
        form_title.setStyleSheet("color: #000000; margin-bottom: 10px;")
        content_layout.addWidget(form_title)

        # --------------------------------------------------------
        # PERBAIKAN UTAMA: IMPLEMENTASI QSCROLLAREA
        # --------------------------------------------------------
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        # White Box Card Area (Sekarang dibungkus oleh scroll_area)
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
            QLineEdit, QComboBox {
                border: 1px solid #A0A0A0;
                border-radius: 8px;
                padding: 4px;
                background-color: white;
                color: black;
                font-size: 13px;
            }
            QCheckBox { background: transparent; }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #A0A0A0;
                border-radius: 4px;
                background: white;
            }
            QCheckBox::indicator:checked {
                background: #0078D7;
                border: 1px solid #0078D7;
                image: url(check.png);
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

        # Master Grid Layout
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)

        # --- KOLOM KIRI (STATUS + ANGIN + VISIBILITY) ---
        left_box = QVBoxLayout()
        left_box.setSpacing(15)

# [1] SECTION: STATUS METAR (Eksklusif - Hanya Bisa Pilih Satu)
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame { 
                border: 1px solid #C9D6E5; 
                padding: 12px; 
                border-radius: 8px;
                background-color: #EBF3FC;
            }
            QLabel { border: none; background: transparent; padding: 0px; color: black; }
            QCheckBox {
                color: black;
                font-weight: bold;
                font-size: 13px;
                background: transparent;
            }
        """)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setSpacing(10)
        status_layout.setContentsMargins(12, 12, 12, 12)
        
        status_title = QLabel("STATUS METAR")
        status_title.setObjectName("SectionTitle")
        status_title.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        status_layout.addWidget(status_title)

        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(20)
        
        self.check_cor = QCheckBox("COR")
        self.check_nil = QCheckBox("NIL")
        self.check_auto = QCheckBox("AUTO")
        
        # PERBAIKAN UTAMA: Membuat grup eksklusif khusus untuk ketiga Checkbox status
        self.status_group = QButtonGroup(self)
        self.status_group.setExclusive(True)
        
        # Masukkan checkbox ke dalam grup
        self.status_group.addButton(self.check_cor)
        self.status_group.addButton(self.check_nil)
        self.status_group.addButton(self.check_auto)
        
        checkbox_layout.addWidget(self.check_cor)
        checkbox_layout.addWidget(self.check_nil)
        checkbox_layout.addWidget(self.check_auto)
        checkbox_layout.addStretch()
        
        status_layout.addLayout(checkbox_layout)
        left_box.addWidget(status_frame)
        
        # [2] SECTION: ANGIN
        angin_frame = QFrame()
        angin_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #D0D0D0; 
                padding: 12px; 
                border-radius: 8px;
                background-color: white;
            }
            QLabel { border: none; background: transparent; padding: 0px; color: #000000; }
            QLineEdit { min-height: 22px; max-height: 22px; }
        """)
        angin_layout = QGridLayout(angin_frame)
        angin_layout.setSpacing(12)
        angin_layout.setContentsMargins(12, 12, 12, 12)
        
        angin_title = QLabel("ANGIN")
        angin_title.setObjectName("SectionTitle")
        angin_title.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        angin_layout.addWidget(angin_title, 0, 0, 1, 2)
        
        lbl_arah = QLabel("Arah Angin")
        angin_layout.addWidget(lbl_arah, 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        arah_layout = QHBoxLayout()
        arah_layout.setContentsMargins(0, 0, 0, 0)
        arah_layout.setSpacing(8)

        self.input_arah_angin = QLineEdit()
        arah_layout.addWidget(self.input_arah_angin)

        vrb_label = QLabel("VRB")
        vrb_label.setStyleSheet("font-weight: bold;")
        arah_layout.addWidget(vrb_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.checkbox_vrb_arah = QCheckBox("")
        arah_layout.addWidget(self.checkbox_vrb_arah, 0, Qt.AlignmentFlag.AlignVCenter)
        arah_layout.addStretch()

        angin_layout.addLayout(arah_layout, 1, 1)

        lbl_kecepatan = QLabel("Kecepatan Angin")
        angin_layout.addWidget(lbl_kecepatan, 2, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.input_kecepatan_angin = QLineEdit()
        angin_layout.addWidget(self.input_kecepatan_angin, 2, 1)

        lbl_variasi = QLabel("Variasi Angin")
        lbl_variasi.setStyleSheet("font-weight: bold;")
        angin_layout.addWidget(lbl_variasi, 3, 0, 1, 2, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        var_layout = QHBoxLayout()
        var_layout.setContentsMargins(0, 0, 0, 0)
        var_layout.setSpacing(8)
        
        lbl_min = QLabel("Arah min")
        self.input_arah_min = QLineEdit()
        lbl_max = QLabel("Arah max")
        self.input_arah_max = QLineEdit()
        
        var_layout.addWidget(lbl_min, 0, Qt.AlignmentFlag.AlignVCenter)
        var_layout.addWidget(self.input_arah_min)
        var_layout.addWidget(lbl_max, 0, Qt.AlignmentFlag.AlignVCenter)
        var_layout.addWidget(self.input_arah_max)
        
        angin_layout.addLayout(var_layout, 4, 0, 1, 2)
        left_box.addWidget(angin_frame)

        # [3] SECTION: VISIBILITY
        vis_frame = QFrame()
        vis_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #D0D0D0; 
                padding: 12px; 
                border-radius: 8px;
                background-color: white;
            }
            QLabel { border: none; background: transparent; padding: 0px; color: #000000; }
            QLineEdit, QComboBox { min-height: 22px; max-height: 22px; }
        """)
        vis_layout = QGridLayout(vis_frame)
        vis_layout.setSpacing(12)
        vis_layout.setContentsMargins(12, 12, 12, 12)
        
        vis_title = QLabel("VISIBILITY")
        vis_title.setObjectName("SectionTitle")
        vis_title.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        vis_layout.addWidget(vis_title, 0, 0, 1, 2)
        
        vis_layout.addWidget(QLabel("Prevailing (m)"), 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        prevailing_layout = QHBoxLayout()
        prevailing_layout.setContentsMargins(0, 0, 0, 0)
        prevailing_layout.setSpacing(8)

        self.input_prevailing = QLineEdit()
        prevailing_layout.addWidget(self.input_prevailing)
        
        ndv_label = QLabel("NDV")
        ndv_label.setStyleSheet("font-weight: bold;")
        prevailing_layout.addWidget(ndv_label, 0, Qt.AlignmentFlag.AlignVCenter)
        
        self.checkbox_ndv = QCheckBox("")
        prevailing_layout.addWidget(self.checkbox_ndv, 0, Qt.AlignmentFlag.AlignVCenter)
        prevailing_layout.addStretch()

        vis_layout.addLayout(prevailing_layout, 1, 1)

        vis_layout.addWidget(QLabel("Minimum"), 2, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.input_minimum = QLineEdit()
        vis_layout.addWidget(self.input_minimum, 2, 1)
        
        vis_layout.addWidget(QLabel("Min Vis Direction"), 3, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.input_min_vis_dir = QLineEdit()
        vis_layout.addWidget(self.input_min_vis_dir, 3, 1)

        left_box.addWidget(vis_frame)
        grid_layout.addLayout(left_box, 0, 0) 

        # --- KOLOM KANAN (WAKTU + AWAN + KUALITAS UDARA) ---
        right_box = QVBoxLayout()
        right_box.setSpacing(15)

        # --- Section Waktu ---
        waktu_frame = QFrame()
        waktu_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #D0D0D0; 
                padding: 10px; 
                border-radius: 8px;
                background-color: white;
            }
            QLabel { border: none; background: transparent; padding: 0px; }
        """)
        waktu_layout = QHBoxLayout(waktu_frame)
        waktu_layout.setContentsMargins(12, 8, 12, 8)
        
        waktu_title = QLabel("WAKTU")
        waktu_title.setObjectName("SectionTitle")
        waktu_title.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        waktu_layout.addWidget(waktu_title, 0, Qt.AlignmentFlag.AlignVCenter)
        waktu_layout.addStretch()

        waktu_input_layout = QHBoxLayout()
        waktu_input_layout.setSpacing(5)

        self.input_jam = QLineEdit()
        self.input_jam.setPlaceholderText("HH")
        self.input_jam.setFixedWidth(45)
        self.input_jam.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_jam.setStyleSheet("min-height: 22px; max-height: 22px;")

        titik_dua = QLabel(":")
        titik_dua.setStyleSheet("color: black; font-weight: bold; background: transparent;")

        self.input_menit = QLineEdit()
        self.input_menit.setPlaceholderText("MM")
        self.input_menit.setFixedWidth(45)
        self.input_menit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_menit.setStyleSheet("min-height: 22px; max-height: 22px;")

        waktu_input_layout.addWidget(self.input_jam)
        waktu_input_layout.addWidget(titik_dua)
        waktu_input_layout.addWidget(self.input_menit)

        waktu_layout.addLayout(waktu_input_layout)
        right_box.addWidget(waktu_frame)

        # --- Section Awan ---
        awan_frame = QFrame()
        awan_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #D0D0D0; 
                padding: 12px; 
                border-radius: 8px;
                background-color: white;
            }
            QLabel { border: none; background: transparent; padding: 0px; color: black; }
            QLineEdit { min-height: 22px; max-height: 22px; }
        """)
        awan_layout = QGridLayout(awan_frame)
        awan_layout.setSpacing(12)
        awan_layout.setContentsMargins(12, 12, 12, 12)
        
        awan_title = QLabel("AWAN")
        awan_title.setObjectName("SectionTitle")
        awan_title.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        awan_layout.addWidget(awan_title, 0, 0, 1, 2)   

        awan_layout.addWidget(QLabel("Jumlah"), 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.input_jumlah_awan = QLineEdit()
        awan_layout.addWidget(self.input_jumlah_awan, 1, 1)

        awan_layout.addWidget(QLabel("Tinggi (FEET)"), 2, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.input_tinggi_awan = QLineEdit()
        awan_layout.addWidget(self.input_tinggi_awan, 2, 1)
        
        awan_layout.setColumnStretch(0, 0)
        awan_layout.setColumnStretch(1, 1)
        right_box.addWidget(awan_frame)

        # --- Section Kualitas Udara ---
        ku_frame = QFrame()
        ku_frame.setStyleSheet("""
            QFrame { 
                border: 1px solid #D0D0D0; 
                padding: 12px; 
                border-radius: 8px;
                background-color: white;
            }
            QLabel { border: none; background: transparent; padding: 0px; color: black; }
            QLineEdit { min-height: 22px; max-height: 22px; }
        """)
        ku_layout = QGridLayout(ku_frame)
        ku_layout.setSpacing(12)
        ku_layout.setContentsMargins(12, 12, 12, 12)
        
        ku_title = QLabel("KUALITAS UDARA")
        ku_title.setObjectName("SectionTitle")
        ku_title.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        ku_layout.addWidget(ku_title, 0, 0, 1, 2)

        ku_layout.addWidget(QLabel("Temperatur ℃"), 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.input_temp = QLineEdit()
        ku_layout.addWidget(self.input_temp, 1, 1)

        ku_layout.addWidget(QLabel("Titik Embun ℃"), 2, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.input_embun = QLineEdit()
        ku_layout.addWidget(self.input_embun, 2, 1)

        ku_layout.addWidget(QLabel("Tekanan Udara (QNH)"), 3, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.input_tekanan = QLineEdit()
        ku_layout.addWidget(self.input_tekanan, 3, 1)

        ku_layout.setColumnStretch(0, 0)
        ku_layout.setColumnStretch(1, 1)
        right_box.addWidget(ku_frame)

        grid_layout.addLayout(right_box, 0, 1)
        card_layout.addLayout(grid_layout)
        card_layout.addStretch()

        # ==========================================
        # 3. ACTION BUTTONS (BATAL & KIRIM DATA)
        # ==========================================
        action_btn_layout = QHBoxLayout()
        action_btn_layout.addStretch()

        batal_btn = QPushButton("BATAL")
        batal_btn.setStyleSheet("""
            QPushButton {
                background-color: red;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
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
                border-radius: 4px;
                padding: 8px 40px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #0000CD; }
        """)

        action_btn_layout.addWidget(batal_btn)
        action_btn_layout.addSpacing(20)
        action_btn_layout.addWidget(kirim_btn)
        card_layout.addLayout(action_btn_layout)

        # Memasukkan card_widget ke dalam scroll_area
        scroll_area.setWidget(card_widget)
        content_layout.addWidget(scroll_area)
        
        body_layout.addWidget(content_container)
        main_layout.addLayout(body_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        if self.data_metar:
            self.isi_data_ke_form()

        kirim_btn.clicked.connect(self.proses_kirim)

    def isi_data_ke_form(self):
        # Sesuaikan indeks [0], [1], dst dengan urutan query SELECT Anda di Dashboard
        # Contoh urutan data: waktu, arah, kec, vis, tinggi, temp, embun
        d = self.data_metar

        if 'raw_metar' in d.keys():
            self.input_metar.setText(str(d['raw_metar']))
        
        # Waktu (Contoh: "05:30")
        waktu_str = d['waktu_observasi'] # Contoh: "06:00"
        if waktu_str and ":" in waktu_str:
            jam, menit = waktu_str.split(":")
            self.input_jam.setText(jam)
            self.input_menit.setText(menit)
        
        self.input_arah_angin.setText(str(d['wind_direction']))
        self.input_kecepatan_angin.setText(str(d['wind_speed']))
        self.input_arah_min.setText(str(d['wind_dir_min']))
        self.input_arah_max.setText(str(d['wind_dir_max']))
        self.input_prevailing.setText(str(d['visibility_prevailing']))
        self.input_jumlah_awan.setText(str(d['cloud_cover']))
        self.input_tinggi_awan.setText(str(d['cloud_height']))
        self.input_temp.setText(str(d['temperature']))
        self.input_embun.setText(str(d['dewpoint']))
        self.input_tekanan.setText(str(d['pressure']))          # Tekanan

    def proses_kirim(self):
        from fill_form2 import run_test
        d = self.data_metar  # Ambil data dari form_dashboard.py
        # Ambil data terbaru dari form (jika user mengedit manual)
        data_final = {
            "full_date": d['tanggal_observasi'], # Ambil dari database
            "hour": self.input_jam.text(),
            "minute": self.input_menit.text(),
            "direction": self.input_arah_angin.text(),
            "speed": self.input_kecepatan_angin.text(),
            "dir_min": self.input_arah_min.text(),
            "dir_max": self.input_arah_max.text(),
            "visibility": self.input_prevailing.text(),
            "cloud_amount": self.input_jumlah_awan.text(),
            "cloud_height": self.input_tinggi_awan.text(),
            "temp": self.input_temp.text(),
            "dew_point": self.input_embun.text(),
            "pressure": self.input_tekanan.text()
            # ... sesuaikan key dengan apa yang diminta fill_form2.py
        }
        
        # Jalankan proses kirim
        # self.worker = PlaywrightWorker(data_final)
        # self.worker.selesai.connect(self.on_kirim_selesai)
        # self.worker.start()
        nama_user = self.user_data.get("nama", "Observer")
        run_test(data_final, nama_user)
        QMessageBox.information(self, "Berhasil", "Data sedang dikirim ke BMKGSatu!")

    def perbarui_sesi_login(self):
        sender_btn = self.sender()
        if sender_btn is not None:
            sender_btn.setChecked(False)

        msg = QMessageBox(self)
        msg.setWindowTitle("Perbarui Sesi Login")
        msg.setIcon(QMessageBox.Information)
        msg.setText("Browser akan terbuka untuk login BMKGSatu.\n\n"
                    "Silakan login secara manual, lalu klik tombol 'Resume' atau 'F8' pada "
                    "jendela Playwright Inspector agar sesi login tersimpan.")
        msg.setStyleSheet("QLabel{color: black;} QPushButton{color: black;}")
        msg.exec()

        self.session_worker = SessionUpdateWorker()
        self.session_worker.selesai.connect(self.on_sesi_login_selesai)
        self.session_worker.start()

    def on_sesi_login_selesai(self, sukses, pesan):
        msg = QMessageBox(self)
        if sukses:
            msg.setWindowTitle("Berhasil")
            msg.setIcon(QMessageBox.Information)
        else:
            msg.setWindowTitle("Gagal")
            msg.setIcon(QMessageBox.Critical)
            
        msg.setText(pesan)
        msg.setStyleSheet("QLabel{color: black;} QPushButton{color: black;}")
        msg.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MetarApp()
    window.show()
    sys.exit(app.exec())
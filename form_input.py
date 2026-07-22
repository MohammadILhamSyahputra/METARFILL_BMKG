import sqlite3
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFrame, QGridLayout, QSpacerItem, 
    QSizePolicy, QButtonGroup, QCheckBox, QComboBox, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QFont, QIcon

from auth_utils import get_db_path
from session_worker import SessionUpdateWorker
from datetime import datetime

class MetarApp(QMainWindow):
    def __init__(self, data_metar=None, user_data=None, parent_window=None):
        super().__init__()
        self.data_metar = data_metar
        self.user_data = user_data or {"id_user": None, "nama": "Zenita Endriani", "role": "Observer"}
        self.parent_window = parent_window
        self.setWindowTitle("Stasiun Meteorologi Kelas III Dhoho Kediri")
        self.resize(1100, 700) 
        self.setStyleSheet("background-color: #F0F4F8; font-family: 'Segoe UI', Arial, sans-serif;")

        # Main Layout: Top Header + Bottom Content
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # HEADER SECTION
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
        logo_title_layout = QHBoxLayout()
        logo_label = QLabel()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        pixmap_logo = QPixmap(os.path.join(current_dir, "logo-bmkg.png"))        
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

        # BODY SECTION 
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

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
        for idx, item in enumerate(menu_items):
            btn = QPushButton(item)
            btn.setCheckable(True)
            self.menu_group.addButton(btn, idx)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        self.logout_btn = QPushButton("LOGOUT")
        self.logout_btn.setObjectName("LogoutBtn")
        sidebar_layout.addWidget(self.logout_btn)
        body_layout.addWidget(sidebar)
        self.menu_group.idClicked.connect(self.handle_menu_click)
        self.logout_btn.clicked.connect(self.proses_logout)

        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 20, 30, 20)

        form_title = QLabel("Form Input & Preview")
        form_title.setFont(QFont("Arial", 16, QFont.Bold))
        form_title.setStyleSheet("color: #000000; margin-bottom: 10px;")
        content_layout.addWidget(form_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")
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

        # KOLOM KIRI (STATUS + ANGIN + VISIBILITY)
        left_box = QVBoxLayout()
        left_box.setSpacing(15)
        
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
        self.status_group = QButtonGroup(self)
        self.status_group.setExclusive(True)        
        self.status_group.addButton(self.check_cor)
        self.status_group.addButton(self.check_nil)
        self.status_group.addButton(self.check_auto)
        
        checkbox_layout.addWidget(self.check_cor)
        checkbox_layout.addWidget(self.check_nil)
        checkbox_layout.addWidget(self.check_auto)
        checkbox_layout.addStretch()
        
        status_layout.addLayout(checkbox_layout)
        left_box.addWidget(status_frame)
        
        # SECTION ANGIN
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
        self.input_kecepatan_angin.textChanged.connect(self._perbarui_checkbox_vrb)

        lbl_gust = QLabel("Gust")
        angin_layout.addWidget(lbl_gust, 3, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.input_gust = QLineEdit()
        angin_layout.addWidget(self.input_gust, 3, 1)

        lbl_variasi = QLabel("Variasi Angin")
        lbl_variasi.setStyleSheet("font-weight: bold;")
        angin_layout.addWidget(lbl_variasi, 4, 0, 1, 2, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
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
        
        angin_layout.addLayout(var_layout, 5, 0, 1, 2)
        left_box.addWidget(angin_frame)

        # SECTION VISIBILITY
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

        # SECTION TREND
        trend_frame = QFrame()
        trend_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #D0D0D0; 
                padding: 12px; 
                border-radius: 8px;
                background-color: white;
            }
            QLabel { border: none; background: transparent; padding: 0px; color: #000000; }
            QLineEdit { min-height: 22px; max-height: 22px; }
        """)
        trend_layout = QGridLayout(trend_frame)
        trend_layout.setSpacing(12)
        trend_layout.setContentsMargins(12, 12, 12, 12)

        trend_title = QLabel("TREND")
        trend_title.setObjectName("SectionTitle")
        trend_title.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        trend_layout.addWidget(trend_title, 0, 0, 1, 2)

        trend_layout.addWidget(QLabel("Trend"), 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.input_trend = QLineEdit()
        trend_layout.addWidget(self.input_trend, 1, 1)

        trend_layout.setColumnStretch(0, 0)
        trend_layout.setColumnStretch(1, 1)

        left_box.addWidget(trend_frame)
        left_box.addStretch() 
        grid_layout.addLayout(left_box, 0, 0, Qt.AlignmentFlag.AlignTop)

        # KOLOM KANAN 
        right_box = QVBoxLayout()
        right_box.setSpacing(15)

        # Section Waktu
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

        # section pengamatan
        cuaca_frame = QFrame()
        cuaca_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #D0D0D0; 
                padding: 12px; 
                border-radius: 8px;
                background-color: white;
            }
            QLabel { border: none; background: transparent; padding: 0px; color: black; }
            QLineEdit, QComboBox { min-height: 24px; max-height: 24px; }
        """)
        cuaca_layout = QVBoxLayout(cuaca_frame)
        cuaca_layout.setSpacing(8)
        cuaca_layout.setContentsMargins(12, 12, 12, 12)

        # Cuaca Saat Pengamatan
        lbl_cuaca_saat = QLabel("CUACA SAAT PENGAMATAN")
        lbl_cuaca_saat.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        cuaca_layout.addWidget(lbl_cuaca_saat)
        lbl_group1_saat = QLabel("Group 1")
        lbl_group1_saat.setStyleSheet("font-weight: bold; font-size: 13px; margin-bottom: 2px;")
        
        self.input_cuaca_saat = QLineEdit()
        cuaca_layout.addWidget(lbl_group1_saat)
        cuaca_layout.addWidget(self.input_cuaca_saat)
        cuaca_layout.addSpacing(5)

        # Cuaca Yang Lalu
        lbl_cuaca_lalu = QLabel("CUACA YANG LALU")
        lbl_cuaca_lalu.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        lbl_group1_lalu = QLabel("Group 1")
        lbl_group1_lalu.setStyleSheet("font-weight: bold; font-size: 13px; margin-bottom: 2px;")
        
        self.combo_cuaca_lalu = QLineEdit()
        cuaca_layout.addWidget(lbl_cuaca_lalu)  
        cuaca_layout.addWidget(lbl_group1_lalu)
        cuaca_layout.addWidget(self.combo_cuaca_lalu)

        right_box.addWidget(cuaca_frame)

        # SECTION AWAN 
        awan_frame = QFrame()
        awan_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #D0D0D0; 
                padding: 12px; 
                border-radius: 8px;
                background-color: white;
            }
            QLabel { border: none; background: transparent; padding: 0px; color: black; }
            QLabel#TableHeaderTitle {
                font-weight: bold;
                color: #555555;
                font-size: 11px;
            }
            QLineEdit { min-height: 24px; max-height: 24px; }
        """)
        
        awan_layout = QGridLayout(awan_frame)
        awan_layout.setSpacing(10)
        awan_layout.setContentsMargins(12, 12, 12, 12)
        
        awan_title = QLabel("AWAN")
        awan_title.setObjectName("SectionTitle")
        awan_title.setStyleSheet("color: blue; font-size: 12px; font-weight: bold;")
        awan_layout.addWidget(awan_title, 0, 0, 1, 3)   

        lbl_h_jumlah = QLabel("JUMLAH")
        lbl_h_jumlah.setObjectName("TableHeaderTitle, color: #555555; font-size: 11px; font-weight: bold;")
        lbl_h_tinggi = QLabel("TINGGI (FEET)")
        lbl_h_tinggi.setObjectName("TableHeaderTitle, color: #555555; font-size: 11px; font-weight: bold;")
        lbl_h_type = QLabel("TYPE")
        lbl_h_type.setObjectName("TableHeaderTitle, color: #555555; font-size: 11px; font-weight: bold;")
        
        awan_layout.addWidget(lbl_h_jumlah, 1, 0, Qt.AlignmentFlag.AlignCenter)
        awan_layout.addWidget(lbl_h_tinggi, 1, 1, Qt.AlignmentFlag.AlignCenter)
        awan_layout.addWidget(lbl_h_type, 1, 2, Qt.AlignmentFlag.AlignCenter)

        self.input_jumlah_awan1 = QLineEdit()
        self.input_tinggi_awan1 = QLineEdit()
        self.input_tipe_awan1 = QLineEdit()
        
        awan_layout.addWidget(self.input_jumlah_awan1, 2, 0)
        awan_layout.addWidget(self.input_tinggi_awan1, 2, 1)
        awan_layout.addWidget(self.input_tipe_awan1, 2, 2)

        # Baris Awan 2
        self.input_jumlah_awan2 = QLineEdit()
        self.input_tinggi_awan2 = QLineEdit()
        self.input_tipe_awan2 = QLineEdit()
        
        awan_layout.addWidget(self.input_jumlah_awan2, 3, 0)
        awan_layout.addWidget(self.input_tinggi_awan2, 3, 1)
        awan_layout.addWidget(self.input_tipe_awan2, 3, 2)

        # Baris Awan 3
        self.input_jumlah_awan3 = QLineEdit()
        self.input_tinggi_awan3 = QLineEdit()
        self.input_tipe_awan3 = QLineEdit()
        
        awan_layout.addWidget(self.input_jumlah_awan3, 4, 0)
        awan_layout.addWidget(self.input_tinggi_awan3, 4, 1)
        awan_layout.addWidget(self.input_tipe_awan3, 4, 2)

        # Input Vertical Vis di baris paling bawah tabel awan
        lbl_v_vis = QLabel("VERTICAL VIS")
        lbl_v_vis.setStyleSheet("font-weight: bold; margin-top: 5px;")
        self.input_vertical_vis = QLineEdit()
        self.input_vertical_vis.setPlaceholderText("Feet...")
        
        awan_layout.addWidget(lbl_v_vis, 5, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        awan_layout.addWidget(self.input_vertical_vis, 5, 1, 1, 2) # Mengambil sisa 2 kolom ke kanan

        awan_layout.setColumnStretch(0, 1)
        awan_layout.setColumnStretch(1, 1)
        awan_layout.setColumnStretch(2, 1)
        
        right_box.addWidget(awan_frame)
        # Section Kualitas Udara 
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

        right_box.addStretch() 
        grid_layout.addLayout(right_box, 0, 1, Qt.AlignmentFlag.AlignTop)        
        card_layout.addLayout(grid_layout)

        # ACTION BUTTONS (BATAL & KIRIM DATA)
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
        
        self.kirim_btn = QPushButton("KIRIM DATA")
        self.kirim_btn.setStyleSheet("""
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
            QPushButton:disabled { background-color: #9FA8DA; }
        """)

        action_btn_layout.addWidget(batal_btn)
        action_btn_layout.addSpacing(20)
        action_btn_layout.addWidget(self.kirim_btn)
        card_layout.addLayout(action_btn_layout)

        scroll_area.setWidget(card_widget)
        content_layout.addWidget(scroll_area)
        
        body_layout.addWidget(content_container)
        main_layout.addLayout(body_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        if self.data_metar:
            self.isi_data_ke_form()

        self.kirim_btn.clicked.connect(self.proses_kirim)
        batal_btn.clicked.connect(self.batal_kirim)

    def batal_kirim(self):
        if self.parent_window:
            self.parent_window.show() 
        self.close()

    def _perbarui_checkbox_vrb(self):
        teks_kecepatan = self.input_kecepatan_angin.text().strip()
        try:
            kecepatan_angin = float(teks_kecepatan) if teks_kecepatan else 0
        except ValueError:
            kecepatan_angin = 0
        self.checkbox_vrb_arah.setChecked(kecepatan_angin > 2)

    def isi_data_ke_form(self):
        d = self.data_metar
        data_dict = dict(d)
        print(data_dict)
        print("RAW =", repr(data_dict.get("raw_metar"))) 
        
        print(f"DEBUG: Data dictionary: {data_dict}")
        print(f"DEBUG: Isi lengkap data_metar: {d}")

        try:
            raw_metar_value = d['raw_metar']
        except (IndexError, KeyError):
            raw_metar_value = None

        if raw_metar_value:
            self.input_metar.setText(str(raw_metar_value))
            print("TEXTBOX =", self.input_metar.text())
        else:
            print("DEBUG: 'raw_metar' tidak ditemukan / kosong pada data_metar yang dikirim ke form ini.")

        self.check_cor.setChecked(False)
        self.check_nil.setChecked(False)
        self.check_auto.setChecked(False)
        self.input_cuaca_saat.setText("")
        self.combo_cuaca_lalu.setText("")

        parsed = None
        if raw_metar_value:
            try:
                from parser import parse_metar
                parsed = parse_metar(str(raw_metar_value))
            except Exception as e:
                parsed = None
                print(f"DEBUG: Gagal re-parse raw_metar untuk checklist COR/NIL/AUTO/cuaca: {e}")

            if parsed:
                if parsed.get("is_cor"):
                    self.check_cor.setChecked(True)
                elif parsed.get("is_nil"):
                    self.check_nil.setChecked(True)
                elif parsed.get("is_auto"):
                    self.check_auto.setChecked(True)

                bagian_cuaca_saat = [
                    parsed.get("weather_intensity") or "",
                    parsed.get("weather_descriptor") or "",
                    parsed.get("weather_precipitation") or parsed.get("weather_obscuration") or parsed.get("weather_other") or "",
                ]
                teks_cuaca_saat = "".join(bagian_cuaca_saat).strip()
                if teks_cuaca_saat:
                    self.input_cuaca_saat.setText(teks_cuaca_saat)

                if parsed.get("recent_weather"):
                    self.combo_cuaca_lalu.setText(parsed["recent_weather"])
        
        waktu_str = d['waktu_observasi'] 
        if waktu_str and ":" in waktu_str:
            jam, menit = waktu_str.split(":")
            self.input_jam.setText(jam)
            self.input_menit.setText(menit)
        
        self.input_arah_angin.setText(str(d['wind_direction']))
        self.input_kecepatan_angin.setText(str(d['wind_speed']))
        if parsed and "is_vrb" in parsed:
            self.checkbox_vrb_arah.setChecked(bool(parsed.get("is_vrb")))
        else:
            self._perbarui_checkbox_vrb()
        self.input_gust.setText(str(data_dict.get('wind_gust', '0')))
        self.input_arah_min.setText(str(d['wind_dir_min']))
        self.input_arah_max.setText(str(d['wind_dir_max']))
        self.input_prevailing.setText(str(d['visibility_prevailing']))
        awan_data = data_dict.get('clouds', []) 
        
        inputs = [
            (self.input_jumlah_awan1, self.input_tinggi_awan1, self.input_tipe_awan1),
            (self.input_jumlah_awan2, self.input_tinggi_awan2, self.input_tipe_awan2),
            (self.input_jumlah_awan3, self.input_tinggi_awan3, self.input_tipe_awan3)
        ]
        
        for i, awan in enumerate(awan_data):
            if i < len(inputs):
                inputs[i][0].setText(str(awan.get('cloud_amount', '')))
                inputs[i][1].setText(str(awan.get('cloud_height', '')))
                inputs[i][2].setText(str(awan.get('cloud_type', '')))

        self.input_temp.setText(str(d['temperature']))
        self.input_embun.setText(str(d['dewpoint']))
        self.input_tekanan.setText(str(d['pressure']))
        self.input_trend.setText(str(data_dict.get('trend', 'NOSIG')))

    def proses_kirim(self):
        d = self.data_metar  
        data_clouds = []
        input_rows = [
            (self.input_jumlah_awan1, self.input_tinggi_awan1, self.input_tipe_awan1),
            (self.input_jumlah_awan2, self.input_tinggi_awan2, self.input_tipe_awan2),
            (self.input_jumlah_awan3, self.input_tinggi_awan3, self.input_tipe_awan3)
        ]
        
        for jumlah, tinggi, tipe in input_rows:
            if jumlah.text().strip():
                data_clouds.append({
                    "amount": jumlah.text().strip(),
                    "height": tinggi.text().strip(),
                    "type": tipe.text().strip()
                })

        is_cor = self.check_cor.isChecked()
        is_nil = self.check_nil.isChecked()
        is_auto = self.check_auto.isChecked()

        is_vrb = self.checkbox_vrb_arah.isChecked()

        teks_cuaca_saat = self.input_cuaca_saat.text().strip()
        try:
            from parser import ekstrak_cuaca
            hasil_cuaca_saat = ekstrak_cuaca(teks_cuaca_saat)
        except Exception as e:
            print(f"DEBUG: Gagal ekstrak_cuaca untuk cuaca saat pengamatan: {e}")
            hasil_cuaca_saat = {
                "weather_intensity": None, "weather_descriptor": None,
                "weather_precipitation": None, "weather_obscuration": None,
                "weather_other": None,
            }

        teks_cuaca_lalu = self.combo_cuaca_lalu.text().strip()

      
        gust_text = self.input_gust.text().strip()
        dir_min_text = self.input_arah_min.text().strip()
        dir_max_text = self.input_arah_max.text().strip()

        gust_final = gust_text if gust_text and gust_text != "0" else None
        dir_min_final = dir_min_text if (is_vrb and dir_min_text) else None
        dir_max_final = dir_max_text if (is_vrb and dir_max_text) else None

        data_final = {
            "full_date": d['tanggal_observasi'], # Ambil dari database
            "hour": self.input_jam.text(),
            "minute": self.input_menit.text(),
            "direction": self.input_arah_angin.text(),
            "speed": self.input_kecepatan_angin.text(),
            "dir_min": dir_min_final,
            "gust": gust_final,
            "dir_max": dir_max_final,
            "visibility": self.input_prevailing.text(),
            "trend": self.input_trend.text(),
            "clouds": data_clouds,
            "temp": self.input_temp.text(),
            "dew_point": self.input_embun.text(),
            "pressure": self.input_tekanan.text(),
            "is_cor": is_cor,
            "is_nil": is_nil,
            "is_auto": is_auto,
            "is_vrb": is_vrb,
            "weather_intensity": hasil_cuaca_saat.get("weather_intensity"),
            "weather_descriptor": hasil_cuaca_saat.get("weather_descriptor"),
            "weather_precipitation": hasil_cuaca_saat.get("weather_precipitation"),
            "weather_obscuration": hasil_cuaca_saat.get("weather_obscuration"),
            "weather_other": hasil_cuaca_saat.get("weather_other"),
            "recent_weather": teks_cuaca_lalu or None,
        }
        
        nama_user = self.user_data.get("nama", "Observer")
        id_user = self.user_data.get("id_user")
        id_metar = d['id_metar']

        self._kirim_id_user = id_user
        self._kirim_id_metar = id_metar

        from kirim_worker import KirimWorker

        self.kirim_btn.setEnabled(False)
        self.kirim_btn.setText("MENGIRIM...")

        self.kirim_worker = KirimWorker(data_final, nama_user, parent=self)
        self.kirim_worker.selesai.connect(self._kirim_selesai)
        self.kirim_worker.gagal.connect(self._kirim_gagal)
        self.kirim_worker.start()

    def _kirim_selesai(self):
        self.kirim_btn.setEnabled(True)
        self.kirim_btn.setText("KIRIM DATA")
        self.simpan_ke_history(self._kirim_id_user, self._kirim_id_metar, "SUKSES")
        msg = QMessageBox(self)
        msg.setWindowTitle("Berhasil")
        msg.setIcon(QMessageBox.Information)
        msg.setText("Data berhasil dikirim ke BMKGSatu dan riwayat tersimpan!")
        msg.setStyleSheet("QLabel{color: black;} QPushButton{color: black;}")
        msg.exec()

    def _kirim_gagal(self, pesan_error):
        self.kirim_btn.setEnabled(True)
        self.kirim_btn.setText("KIRIM DATA")
        self.simpan_ke_history(self._kirim_id_user, self._kirim_id_metar, "GAGAL")
        msg = QMessageBox(self)
        msg.setWindowTitle("Error")
        msg.setIcon(QMessageBox.Critical)
        msg.setText(f"Pengiriman gagal: {pesan_error}")
        msg.setStyleSheet("QLabel{color: black;} QPushButton{color: black;}")
        msg.exec()

    def simpan_ke_history(self, id_user, id_metar, status):
        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO AutoFill_History (id_user, id_metar, waktu_send, status) 
            VALUES (?, ?, ?, ?)""", (id_user, id_metar, waktu_sekarang, status)
        )
        
        conn.commit()
        conn.close()

    def handle_menu_click(self, button_id):
        if button_id == 0:
            self.dashboard()
        elif button_id == 1:
            self.buka_riwayat()
        elif button_id == 2:
            self.perbarui_sesi_login()

    def dashboard(self):
        from form_dashboard import DashboardApp
        self.dashboard_window = DashboardApp(user_data=self.user_data)
        self.dashboard_window.show()
        self.close()

    def buka_riwayat(self):
        from form_riwayat_data import RiwayatApp
        self.riwayat_window = RiwayatApp(user_data=self.user_data)
        self.riwayat_window.show()
        self.close()

    def proses_logout(self):
        from login_page import LoginPage
        self.login_window = LoginPage()
        self.login_window.show()
        self.close()

    def perbarui_sesi_login(self):
        sender_btn = self.sender()
        if sender_btn is not None and isinstance(sender_btn, QButtonGroup):
            active_btn = sender_btn.checkedButton()
            if active_btn is not None:
                active_btn.setChecked(False)

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
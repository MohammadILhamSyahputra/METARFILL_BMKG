import sqlite3
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton,QLineEdit, QFrame, QGridLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QButtonGroup, QAbstractItemView,
    QMessageBox, QDateEdit
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QFont

from auth_utils import get_db_path
from session_worker import SessionUpdateWorker
from metar_fetch_worker import MetarFetchWorker
from parser import parse_metar, simpan_ke_db, proses_data_untuk_tanggal
import requests
from datetime import datetime

class DashboardApp(QMainWindow):
    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data or {"id_user": None, "nama": "Zenita Endriani", "role": "Observer"}
        self.setWindowTitle("Stasiun Meteorologi Kelas III Dhoho Kediri - Dashboard")
        self.resize(1100, 700)
        self.setStyleSheet("background-color: #F0F4F8; font-family: 'Segoe UI', Arial, sans-serif;")

        # Main Layout: Top Header + Bottom Content
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

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

        # User Profile
        user_layout = QHBoxLayout()
        user_name = QLabel(self.user_data.get("nama", "Observer"))
        user_name.setFont(QFont("Arial", 11, QFont.Bold))
        
        user_icon = QLabel()
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

        # SIDEBAR 
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
            if item == "Dashboard":
                btn.setChecked(True)

        sidebar_layout.addStretch()

        self.logout_btn = QPushButton("LOGOUT")
        self.logout_btn.setObjectName("LogoutBtn")
        
        sidebar_layout.addWidget(self.logout_btn)
        body_layout.addWidget(sidebar)

        self.logout_btn.clicked.connect(self.proses_logout)

        # --- DASHBOARD CONTENT MAIN AREA ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(20)

        dashboard_title = QLabel("Dashboard Observer")
        dashboard_title.setFont(QFont("Arial", 16, QFont.Bold))
        dashboard_title.setStyleSheet("color: #000000;")
        content_layout.addWidget(dashboard_title)

        # --- CARD CARDS INFO SECTION ---
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        # --- KARTU KIRI (DATA TERAKHIR) ---
        card_terakhir = QFrame()
        card_terakhir.setStyleSheet("background-color: #5B9E63; border-radius: 12px; border: none;")
        layout_c1 = QVBoxLayout(card_terakhir)
        layout_c1.setContentsMargins(15, 12, 15, 12)
        lbl_c1_title = QLabel("Data Terakhir (Jam) Hari Ini")
        lbl_c1_title.setStyleSheet("color: #E2E2E2; font-weight: bold; font-size: 11px;")
        
        # PERBAIKAN: Menggunakan self. agar bisa di-update dari database
        self.lbl_data_terakhir = QLabel("-- : --")
        self.lbl_data_terakhir.setStyleSheet("color: white; font-weight: bold; font-size: 26px; margin-top: 5px;")
        layout_c1.addWidget(lbl_c1_title)
        layout_c1.addWidget(self.lbl_data_terakhir)

        # --- KARTU TENGAH (SESI LOGIN AKTIF) ---
        self.card_sesi = QFrame()
        self.card_sesi.setStyleSheet("background-color: #B58D47; border-radius: 12px; border: none;") 
        layout_c2 = QVBoxLayout(self.card_sesi)
        layout_c2.setContentsMargins(15, 12, 15, 12)
        lbl_c2_title = QLabel("Sesi Login Aktif")
        lbl_c2_title.setStyleSheet("color: #E2E2E2; font-weight: bold; font-size: 11px;")
        self.lbl_status_sesi = QLabel("Memeriksa...") 
        self.lbl_status_sesi.setStyleSheet("color: white; font-weight: bold; font-size: 26px; margin-top: 5px;")
        layout_c2.addWidget(lbl_c2_title)
        layout_c2.addWidget(self.lbl_status_sesi)

        # --- KARTU KANAN (JUMLAH DATA) ---
        card_jumlah = QFrame()
        card_jumlah.setStyleSheet("background-color: #79A9BF; border-radius: 12px; border: none;")
        layout_c3 = QVBoxLayout(card_jumlah)
        layout_c3.setContentsMargins(15, 12, 15, 12)
        lbl_c3_title = QLabel("Jumlah Semua Data METAR")
        lbl_c3_title.setStyleSheet("color: #E2E2E2; font-weight: bold; font-size: 11px;")
        
        self.lbl_jumlah_data = QLabel("0")
        self.lbl_jumlah_data.setStyleSheet("color: white; font-weight: bold; font-size: 26px; margin-top: 5px;")
        layout_c3.addWidget(lbl_c3_title)
        layout_c3.addWidget(self.lbl_jumlah_data)

        cards_layout.addWidget(card_terakhir)
        cards_layout.addWidget(self.card_sesi)
        cards_layout.addWidget(card_jumlah)
        content_layout.addLayout(cards_layout)

        # --- TABEL DATA METAR SECTION ---
        table_section_container = QVBoxLayout()
        table_section_container.setSpacing(10)
        input_button_layout = QHBoxLayout()
        input_button_layout.setSpacing(15) 
        
        table_title = QLabel("Tabel Data Metar")
        table_title.setFont(QFont("Arial", 11, QFont.Bold))
        table_title.setStyleSheet("""
            QLabel {
                color: #000000; 
                margin-top: 15px; /* Menyelaraskan jarak dari kartu di atasnya */
            }
        """)
        self.input_ambil_data = QDateEdit()
        self.input_ambil_data.setCalendarPopup(True)
        self.input_ambil_data.setDisplayFormat("dd-MM-yyyy")
        self.input_ambil_data.setDateTime(datetime.now())
        self.input_ambil_data.setFixedWidth(300)
        self.input_ambil_data.setStyleSheet("""
            QDateEdit {
                border: 1px solid #A0A0A0;
                border-radius: 6px;
                padding: 6px 10px;
                background-color: white;
                color: black;
                font-size: 15px;
                font-weight: bold;
                min-height: 35px;
                max-height: 35px;
                margin-top: 15px;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 1px;
                border-left-color: #A0A0A0;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #F0F4F8;
            }
            QDateEdit::down-arrow {
                subcontrol-origin: content;
                subcontrol-position: center;
                position: relative;
                top: 0px;
                left: 0px;
            }
            QDateEdit::drop-down:hover {
                background-color: #E0E8F5;
            }
        """)
        self.input_ambil_data.setStyleSheet(self.input_ambil_data.styleSheet() + """
            QDateEdit::down-arrow:enabled {
                image: none;
                width: 0px;
                height: 0px;
                border-style: solid;
                border-width: 5px 4px 0 4px;
                border-color: #555555 transparent transparent transparent;
            }
        """)
        kalender_popup = self.input_ambil_data.calendarWidget()
        if kalender_popup:
            kalender_popup.setStyleSheet("""
                QCalendarWidget QWidget {
                    color: black; /* Memaksa semua teks di dalam kalender berwarna hitam */
                    background-color: white;
                }
                QCalendarWidget QMenu {
                    color: black;
                    background-color: white;
                }
                QCalendarWidget QToolButton {
                    color: black;
                    background-color: transparent;
                    font-weight: bold;
                }
                QCalendarWidget QToolButton:hover {
                    background-color: #E0E8F5;
                }
                QCalendarWidget QAbstractItemView:enabled {
                    color: black;
                    background-color: white;
                    selection-background-color: #0070C0;
                    selection-color: white;
                }
            """)
        
        self.btn_ambil_data = QPushButton("Ambil Data Baru")
        btn_ambil_data = self.btn_ambil_data
        btn_ambil_data.setFixedWidth(150)
        btn_ambil_data.setStyleSheet("""
            QPushButton {
                background-color: blue;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 12px;
                min-height: 35px;
                max-height: 35px;
                margin-top: 15px;
            }
            QPushButton:hover { background-color: #0000CD; }
        """)
        
        # Menyusun urutan elemen dari kiri ke kanan
        input_button_layout.addWidget(table_title)
        input_button_layout.addWidget(self.input_ambil_data, 1) 
        input_button_layout.addWidget(btn_ambil_data)
        
        content_layout.addLayout(input_button_layout)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(9)
        self.table_widget.setHorizontalHeaderLabels([
            "Waktu", "Arah Angin", "Kecepatan", "Visibility", "tinggi awan", "Temp", "Embun", "id_metar", "Aksi"
        ])
        
        self.table_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setFocusPolicy(Qt.NoFocus)
        self.table_widget.setAlternatingRowColors(True)
        
        self.table_widget.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                gridline-color: #E0E0E0;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                selection-background-color: transparent;
                selection-color: #000000;
            }
            QTableWidget::item:alternate {
                background-color: #F9F9F9;
            }
            QTableWidget::item {
                color: #000000; 
                font-weight: normal;
                font-size: 12px;
                padding-left: 10px;
            }
            QTableWidget::item:focus {
                background-color: transparent;
                border: none;
            }
            QHeaderView::section {
                background-color: #F0F4F8; 
                color: #000000; 
                font-weight: bold;
                font-size: 12px;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #D0D0D0;
            }
        """)    
            
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setRowCount(0)  

        content_layout.addWidget(self.table_widget)
        body_layout.addWidget(content_container)
        main_layout.addLayout(body_layout)

        # Set Central Widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Hubungkan Sinyal & Aksi Tombol
        self.menu_group.idClicked.connect(self.handle_menu_click)
        btn_ambil_data.clicked.connect(self.ambil_data_tanggal)
        self.update_info_status_sesi()
        QTimer.singleShot(0, self.ambil_data_tanggal)

    def load_data_to_table(self, tanggal_filter=None):
        db_path = get_db_path() 
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = """
            SELECT 
                m.waktu_observasi, 
                p.wind_direction, 
                p.wind_speed, 
                p.visibility_prevailing, 
                a1.cloud_height,
                p.temperature, 
                p.dewpoint,
                m.id_metar
            FROM METAR m
            JOIN Parsing_Result p ON m.id_metar = p.id_metar
            LEFT JOIN Awan a1 ON a1.id_parsing = p.id_parsing AND a1.urutan = 1
            {where_clause}
            ORDER BY m.tanggal_observasi DESC, m.waktu_observasi DESC
        """

        if tanggal_filter:
            cursor.execute(
                query.format(where_clause="WHERE m.tanggal_observasi = ?"),
                (tanggal_filter,),
            )
        else:
            cursor.execute(query.format(where_clause=""))
        rows = cursor.fetchall()
        conn.close()

        # Bersihkan tabel sebelum mengisi
        self.table_widget.setRowCount(0)
        
        for row_data in rows:
            row_idx = self.table_widget.rowCount()
            self.table_widget.insertRow(row_idx)
            
            # Memasukkan setiap kolom ke tabel
            for col_idx, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                item.setTextAlignment(Qt.AlignCenter) 
                self.table_widget.setItem(row_idx, col_idx, item)
            
            # Menambahkan tombol "Detail" di kolom terakhir (Aksi)
            btn_detail = QPushButton("Detail")
            btn_detail.setStyleSheet("background-color: #0070C0; color: white; border-radius: 4px;")
            btn_detail.clicked.connect(lambda checked, data=row_data: self.buka_form_input(data[-1])) 
            self.table_widget.setCellWidget(row_idx, 8, btn_detail) 

    def tampilkan_pesan(self, judul, pesan, jenis="info"):
        msg = QMessageBox(self)
        msg.setWindowTitle(judul)
        msg.setText(pesan)
        if jenis == "success":
            msg.setIcon(QMessageBox.Information)
        elif jenis == "warning":
            msg.setIcon(QMessageBox.Warning)
        elif jenis == "error":
            msg.setIcon(QMessageBox.Critical)
        else:
            msg.setIcon(QMessageBox.Information)
        msg.setStyleSheet("QLabel{color: black;} QPushButton{color: black;}")
        msg.exec()

    def _tampilkan_loading(self, pesan="Mengambil data, mohon tunggu..."):
        self._msg_loading = QMessageBox(self)
        self._msg_loading.setWindowTitle("Memproses")
        self._msg_loading.setText(pesan)
        self._msg_loading.setIcon(QMessageBox.Information)
        self._msg_loading.setStandardButtons(QMessageBox.Close)
        self._msg_loading.button(QMessageBox.Close).setText("Tutup")
        self._msg_loading.setStyleSheet("QLabel{color: black;} QPushButton{color: black;}")
        self._msg_loading.show()
        QApplication.processEvents()  # paksa Qt menggambar messagebox sebelum kerja berat dimulai

    def _tutup_loading(self):
        if getattr(self, "_msg_loading", None) is not None:
            self._msg_loading.close()
            self._msg_loading = None

    def ambil_data_tanggal(self):
        if getattr(self, "_fetch_worker", None) is not None and self._fetch_worker.isRunning():
            return

        tanggal_qdate = self.input_ambil_data.date()
        tahun = tanggal_qdate.year()
        bulan = tanggal_qdate.month()
        tanggal = tanggal_qdate.day()
        self._label_tanggal_aktif = f"{tanggal:02d}-{bulan:02d}-{tahun}"
        self._tanggal_filter_aktif = f"{tahun}-{str(bulan).zfill(2)}-{str(tanggal).zfill(2)}"

        self.btn_ambil_data.setEnabled(False)
        self.input_ambil_data.setEnabled(False)

        self._tampilkan_loading(f"Mengambil data METAR tanggal {self._label_tanggal_aktif}...")
        self.statusBar().showMessage(f"Mengambil data METAR tanggal {self._label_tanggal_aktif}...")

        self._fetch_worker = MetarFetchWorker(tahun, bulan, tanggal, parent=self)
        self._fetch_worker.selesai.connect(self._on_fetch_selesai)
        self._fetch_worker.gagal.connect(self._on_fetch_gagal)
        self._fetch_worker.start()

    def _selesaikan_fetch_ui(self):
        self._tutup_loading()
        self.statusBar().clearMessage()
        self.btn_ambil_data.setEnabled(True)
        self.input_ambil_data.setEnabled(True)

    def _on_fetch_selesai(self, ringkasan):
        self._selesaikan_fetch_ui()

        label_tanggal = self._label_tanggal_aktif

        self.load_data_to_table(tanggal_filter=self._tanggal_filter_aktif)
        self.update_info_cards_from_db()

        if ringkasan["total_ditemukan"] == 0:
            self.tampilkan_pesan(
                "Info",
                f"Data METAR WARD tidak ditemukan di server untuk tanggal {label_tanggal}.",
                jenis="warning",
            )
        elif ringkasan["baru"] > 0:
            self.tampilkan_pesan(
                "Berhasil",
                f"{ringkasan['baru']} data METAR baru berhasil disimpan untuk tanggal {label_tanggal}.\n"
                f"({ringkasan['sudah_ada']} sudah ada sebelumnya, "
                f"{ringkasan['gagal_parse']} gagal diparsing.)",
                jenis="success",
            )
        else:
            self.tampilkan_pesan(
                "Info",
                f"Data sudah mutakhir untuk tanggal {label_tanggal} (tidak ada data baru).",
                jenis="info",
            )

    def _on_fetch_gagal(self, pesan_error):
        self._selesaikan_fetch_ui()
        self.tampilkan_pesan(
            "Error", f"Terjadi kesalahan saat mengambil data: {pesan_error}", jenis="error"
        )

    def closeEvent(self, event):
        worker = getattr(self, "_fetch_worker", None)
        if worker is not None and worker.isRunning():
            worker.quit()
            worker.wait(2000)
        super().closeEvent(event)

    def buka_form_input(self, id_metar):
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        query = """
            SELECT m.*, 
                   p.id_parsing, p.wind_direction, p.wind_speed, p.wind_gust, 
                   p.wind_dir_min, p.wind_dir_max, p.visibility_prevailing, 
                   p.temperature, p.dewpoint, p.pressure, p.trend
            FROM METAR m
            JOIN Parsing_Result p ON m.id_metar = p.id_metar
            WHERE m.id_metar = ?
        """
        cursor.execute(query, (id_metar,))
        row = cursor.fetchone()
        
        data_utama = dict(row) if row else None
        
        if data_utama and data_utama.get('id_parsing') is None:
            cursor.execute("SELECT id_parsing FROM Parsing_Result WHERE id_metar = ?", (id_metar,))
            p_row = cursor.fetchone()
            if p_row:
                data_utama['id_parsing'] = p_row['id_parsing']
                print(f"DEBUG: id_parsing berhasil diambil manual: {data_utama['id_parsing']}")
        
        print(f"DEBUG: Data utama ditemukan: {data_utama}")
        
        data_awan = []
        if data_utama and data_utama.get('id_parsing'):
            cursor.execute("SELECT * FROM Awan WHERE id_parsing = ? ORDER BY urutan ASC", 
                           (data_utama['id_parsing'],))
            data_awan = [dict(row) for row in cursor.fetchall()]
        
        conn.close()

        if data_utama:
            data_lengkap = data_utama
            data_lengkap['clouds'] = data_awan 
            print(f"DEBUG DASHBOARD: Data clouds akhir: {data_lengkap.get('clouds')}")
            
            from form_input import MetarApp
            self.form_input_window = MetarApp(data_metar=data_lengkap, user_data=self.user_data, parent_window=self)
            self.form_input_window.show()
            self.close()

    def handle_menu_click(self, button_id):
        if button_id == 1:  
            self.buka_riwayat()
        elif button_id == 2:
            self.perbarui_sesi_login()

    def perbarui_sesi_login(self):
        self.menu_group.button(0).setChecked(True)

        self.tampilkan_pesan(
            "Perbarui Sesi Login",
            "Browser akan terbuka untuk login BMKGSatu.\n\n"
            "Silakan login secara manual, lalu klik tombol 'Resume' atau 'F8' pada "
            "jendela Playwright Inspector agar sesi login tersimpan.",
            jenis="info",
        )

        self.session_worker = SessionUpdateWorker()
        self.session_worker.selesai.connect(self.on_sesi_login_selesai)
        self.session_worker.start()

    def handle_sesi_selesai(self, sukses, pesan):
        if sukses:
            print(pesan)
            self.update_info_status_sesi() 
        else:
            print(f"Error: {pesan}")
            self.lbl_status_sesi.setText("Gagal")
            self.lbl_status_sesi.setStyleSheet("color: #FFD2D2; font-weight: bold; font-size: 26px; margin-top: 5px;")

    def on_sesi_login_selesai(self, sukses, pesan):
        judul = "Berhasil" if sukses else "Gagal"
        jenis = "success" if sukses else "error"
        self.tampilkan_pesan(judul, pesan, jenis=jenis)

    def update_info_status_sesi(self):
        import os
        from datetime import datetime
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        auth_path = os.path.join(current_dir, "auth_state.json")
        
        if os.path.exists(auth_path):
            timestamp = os.path.getmtime(auth_path)
            waktu_modifikasi = datetime.fromtimestamp(timestamp)
            
            self.lbl_status_sesi.setText("Aktif")
            self.lbl_status_sesi.setStyleSheet("color: #FFFFFF; font-size: 24px; font-weight: bold;")
        else:
            self.lbl_status_sesi.setText("Kosong")
            self.lbl_status_sesi.setStyleSheet("color: #FFD2D2; font-size: 24px; font-weight: bold;")

    def update_info_cards_from_db(self):
        try:
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            now = datetime.now()
            current_month_year = now.strftime("%Y-%m")

            query = "SELECT COUNT(*) FROM METAR WHERE strftime('%Y-%m', tanggal_observasi) = ?"
            cursor.execute(query, (current_month_year,))
            total_data_bulan_ini = cursor.fetchone()[0]
            self.lbl_jumlah_data.setText(str(total_data_bulan_ini))
            # cursor.execute("SELECT COUNT(*) FROM METAR")
            # total_data = cursor.fetchone()[0]
            # self.lbl_jumlah_data.setText(str(total_data))

            cursor.execute("SELECT waktu_observasi FROM METAR ORDER BY tanggal_observasi DESC, waktu_observasi DESC LIMIT 1")
            row_waktu = cursor.fetchone()
            
            if row_waktu:
                waktu_raw = row_waktu[0]
                if ":" in waktu_raw:
                    jam, menit = waktu_raw.split(":")
                    self.lbl_data_terakhir.setText(f"{jam} : {menit}")
                else:
                    self.lbl_data_terakhir.setText(waktu_raw)
            else:
                self.lbl_data_terakhir.setText("-- : --")

            conn.close()
        except Exception as e:
            print(f"Gagal memuat info kartu dari database: {e}")

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardApp()
    window.show()
    sys.exit(app.exec())
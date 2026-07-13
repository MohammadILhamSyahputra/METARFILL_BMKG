import sqlite3
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QGridLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QButtonGroup, QAbstractItemView,
    QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFont

from auth_utils import get_db_path
from session_worker import SessionUpdateWorker
from parser import parse_metar, simpan_ke_db
import requests
from datetime import datetime

class DashboardApp(QMainWindow):
    def __init__(self, user_data=None):
        super().__init__()
        # Data user yang sedang login (dikirim dari LoginPage). Diberi nilai
        # default supaya file ini tetap bisa dijalankan mandiri untuk testing.
        self.user_data = user_data or {"id_user": None, "nama": "Zenita Endriani", "role": "Observer"}

        self.setWindowTitle("Stasiun Meteorologi Kelas III Dhoho Kediri - Dashboard")
        self.resize(1100, 700)
        self.setStyleSheet("background-color: #F0F4F8; font-family: 'Segoe UI', Arial, sans-serif;")

        # Main Layout: Top Header + Bottom Content
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================
        # 1. HEADER SECTION (Serasi dengan Form Input)
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

        # Logo BMKG dengan Deteksi Path Absolut
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

        # ==========================================
        # 2. BODY SECTION (Sidebar + Dashboard Content)
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
        for idx, item in enumerate(menu_items):
            btn = QPushButton(item)
            btn.setCheckable(True)
            self.menu_group.addButton(btn, idx) # ID terdaftar aman (0, 1, 2)
            sidebar_layout.addWidget(btn)
            if item == "Dashboard":
                btn.setChecked(True)

        sidebar_layout.addStretch()

        self.logout_btn = QPushButton("LOGOUT")
        self.logout_btn.setObjectName("LogoutBtn")
        
        sidebar_layout.addWidget(self.logout_btn)
        body_layout.addWidget(sidebar)

        # Hubungkan klik tombol ke fungsi logout yang telah dibuat
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

        card_terakhir = QFrame()
        card_terakhir.setStyleSheet("background-color: #5B9E63; border-radius: 12px; border: none;")
        layout_c1 = QVBoxLayout(card_terakhir)
        layout_c1.setContentsMargins(15, 12, 15, 12)
        lbl_c1_title = QLabel("Data Terakhir")
        lbl_c1_title.setStyleSheet("color: #E2E2E2; font-weight: bold; font-size: 11px;")
        lbl_c1_val = QLabel("01 : 30")
        lbl_c1_val.setStyleSheet("color: white; font-weight: bold; font-size: 26px; margin-top: 5px;")
        layout_c1.addWidget(lbl_c1_title)
        layout_c1.addWidget(lbl_c1_val)

        card_otomasi = QFrame()
        card_otomasi.setStyleSheet("background-color: #B58D47; border-radius: 12px; border: none;")
        layout_c2 = QVBoxLayout(card_otomasi)
        layout_c2.setContentsMargins(15, 12, 15, 12)
        lbl_c2_title = QLabel("Status Otomasi")
        lbl_c2_title.setStyleSheet("color: #E2E2E2; font-weight: bold; font-size: 11px;")
        lbl_c2_val = QLabel("Sukses")
        lbl_c2_val.setStyleSheet("color: white; font-weight: bold; font-size: 26px; margin-top: 5px;")
        layout_c2.addWidget(lbl_c2_title)
        layout_c2.addWidget(lbl_c2_val)

        card_jumlah = QFrame()
        card_jumlah.setStyleSheet("background-color: #79A9BF; border-radius: 12px; border: none;")
        layout_c3 = QVBoxLayout(card_jumlah)
        layout_c3.setContentsMargins(15, 12, 15, 12)
        lbl_c3_title = QLabel("Jumlah Data")
        lbl_c3_title.setStyleSheet("color: #E2E2E2; font-weight: bold; font-size: 11px;")
        lbl_c3_val = QLabel("48")
        lbl_c3_val.setStyleSheet("color: white; font-weight: bold; font-size: 26px; margin-top: 5px;")
        layout_c3.addWidget(lbl_c3_title)
        layout_c3.addWidget(lbl_c3_val)

        cards_layout.addWidget(card_terakhir)
        cards_layout.addWidget(card_otomasi)
        cards_layout.addWidget(card_jumlah)
        content_layout.addLayout(cards_layout)

        # --- TABEL DATA METAR SECTION ---
        table_header_layout = QHBoxLayout()
        table_title = QLabel("Tabel Data Metar")
        table_title.setFont(QFont("Arial", 11, QFont.Bold))
        table_title.setStyleSheet("color: #000000;")
        
        btn_ambil_data = QPushButton("Ambil Data Baru")
        btn_ambil_data.setStyleSheet("""
            QPushButton {
                background-color: blue;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 2px;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #0000CD; }
        """)
        
        table_header_layout.addWidget(table_title)
        table_header_layout.addStretch()
        table_header_layout.addWidget(btn_ambil_data)
        content_layout.addLayout(table_header_layout)

        

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

        # PERBAIKAN UTAMA: Mengubah dari .buttonClicked ke .idClicked agar mengirimkan parameter ID int
        self.menu_group.idClicked.connect(self.handle_menu_click)
        btn_ambil_data.clicked.connect(self.refresh_table)
        self.load_data_to_table()

    def load_data_to_table(self):
        db_path = get_db_path() # Pastikan fungsi ini tersedia
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query hanya untuk kolom-kolom yang Anda inginkan
        query = """
            SELECT 
                m.waktu_observasi, 
                p.wind_direction, 
                p.wind_speed, 
                p.visibility_prevailing, 
                p.cloud_height, 
                p.temperature, 
                p.dewpoint,
                m.id_metar
            FROM METAR m
            JOIN Parsing_Result p ON m.id_metar = p.id_metar
            ORDER BY m.tanggal_observasi DESC, m.waktu_observasi DESC
        """
        
        cursor.execute(query)
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
                item.setTextAlignment(Qt.AlignCenter) # Agar lebih rapi di tengah
                self.table_widget.setItem(row_idx, col_idx, item)
            
            # Menambahkan tombol "Detail" di kolom terakhir (Aksi)
            btn_detail = QPushButton("Detail")
            btn_detail.setStyleSheet("background-color: #0070C0; color: white; border-radius: 4px;")
            btn_detail.clicked.connect(lambda checked, data=row_data: self.buka_form_input(data[-1])) # Kirim ID metar
            self.table_widget.setCellWidget(row_idx, 8, btn_detail) # Kolom ke-8 adalah Aksi

    def refresh_table(self):
        # 1. Tambahkan indikator visual (opsional, untuk UX)
        self.statusBar().showMessage("Mengambil data terbaru dari BMKG...")
        QApplication.processEvents() # Agar UI tidak 'freeze' saat download
        
        try:
            # 2. Ambil data dari BMKG
            url = f"https://aviation.bmkg.go.id/latest/metar.php?i=ward&y={datetime.now().year}&m={datetime.now().month}"
            response = requests.get(url, timeout=10) # Tambahkan timeout agar tidak hang
            
            if response.status_code == 200:
                lines = response.text.splitlines()
                metar_lines = [line for line in lines if "METAR WARD" in line]
                
                if not metar_lines:
                    QMessageBox.warning(self, "Info", "Data METAR WARD tidak ditemukan di server.")
                    return

                data_baru_ditemukan = False
                
                # 3. Looping semua baris untuk antisipasi jika ada data yang terlewat
                for line in metar_lines:
                    data = parse_metar(line)
                    if data:
                        status = simpan_ke_db(data, line) # Memanggil fungsi yang sudah kita perbaiki
                        if status == "success":
                            data_baru_ditemukan = True
                
                # 4. Refresh tampilan tabel
                if data_baru_ditemukan:
                    self.load_data_to_table()
                    QMessageBox.information(self, "Berhasil", "Data METAR baru berhasil diperbarui!")
                else:
                    QMessageBox.information(self, "Info", "Data sudah mutakhir (tidak ada data baru).")
            else:
                QMessageBox.critical(self, "Gagal", f"Gagal menghubungi server BMKG (Status: {response.status_code})")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Terjadi kesalahan: {str(e)}")
        
        finally:
            self.statusBar().clearMessage()

    # def buka_form_input(self, data):
    #     from form_input import MetarApp # Pastikan nama kelasnya sama
    #     self.form_input_window = MetarApp(data_metar=data) # Kirim data ke sini
    #     self.form_input_window.show()
    def buka_form_input(self, id_metar): # Terima ID saja
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # PENTING: METAR dan Parsing_Result SAMA-SAMA punya kolom "id_metar"
        # (dan Parsing_Result juga punya "id_parsing"). Jika dipilih dengan
        # "SELECT m.*, p.*", sqlite3.Row akan punya nama kolom duplikat, dan
        # akses berbasis nama seperti d['id_metar'] bisa salah ambil nilai
        # dari tabel yang tidak diharapkan. Karena itu kolom Parsing_Result
        # dipilih secara eksplisit (tanpa id_parsing/id_metar) agar seluruh
        # data (termasuk raw_metar) dari tabel METAR tetap dapat diakses
        # tanpa ambigu.
        query = """
            SELECT 
                m.*, 
                p.wind_direction, p.wind_speed, p.wind_gust,
                p.wind_dir_min, p.wind_dir_max,
                p.visibility_prevailing, p.visibility_minimum,
                p.cloud_cover, p.cloud_height, p.cloud_type, p.vertical_vis,
                p.weather_intensity, p.weather_descriptor,
                p.temperature, p.dewpoint, p.pressure, p.trend
            FROM METAR m
            JOIN Parsing_Result p ON m.id_metar = p.id_metar
            WHERE m.id_metar = ?
        """
        cursor.execute(query, (id_metar,))
        data_lengkap = cursor.fetchone() 
        conn.close()
        print(dict(data_lengkap))
        from form_input import MetarApp
        self.form_input_window = MetarApp(data_metar=data_lengkap, user_data=self.user_data, parent_window=self)
        self.form_input_window.show()
        self.close()

    def handle_menu_click(self, button_id):
        # Jika Riwayat METAR (Index 1) diklik
        if button_id == 1:  
            self.buka_riwayat()
        # Jika Perbarui Sesi Login (Index 2) diklik
        elif button_id == 2:
            self.perbarui_sesi_login()

    def perbarui_sesi_login(self):
        self.menu_group.button(0).setChecked(True)

        # Menggunakan objek QMessageBox kustom agar font hitam tegas
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

    def buka_riwayat(self):
        from form_riwayat_data import RiwayatApp
        self.riwayat_window = RiwayatApp(user_data=self.user_data)
        self.riwayat_window.show()
        self.close()

    def proses_logout(self):
        from login_page import LoginPage
        
        self.login_window = LoginPage()
        self.login_window.show()
        self.close() # Menutup halaman Riwayat

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardApp()
    window.show()
    sys.exit(app.exec())
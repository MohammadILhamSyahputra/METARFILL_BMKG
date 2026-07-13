import sys
import os
from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem, 
    QHeaderView, QButtonGroup, QAbstractItemView, QLineEdit, QMessageBox,
    QComboBox, QDateEdit, QCheckBox
)
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QPixmap, QFont

from session_worker import SessionUpdateWorker
from auth_utils import get_db_path

class RiwayatApp(QMainWindow):
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
        # 1. HEADER SECTION (Serasi)
        # ==========================================
        header = QWidget()
        header.setObjectName("Header")
        header.setMinimumHeight(80)
        header.setStyleSheet("""
            QWidget#Header { background-color: #0070C0; }
            QLabel { color: white; background-color: transparent; border: none; }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # Logo BMKG
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
        # 2. BODY SECTION (Sidebar + Content)
        # ==========================================
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # --- SIDEBAR ---
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            QWidget { background-color: #F8F9FA; border-right: 1px solid #E0E0E0; }
            QPushButton {
                background-color: transparent; border: none; color: #000000;
                text-align: left; padding-left: 20px; font-size: 14px; font-weight: bold; height: 45px;
            }
            QPushButton:hover { background-color: #E8F0FE; }
            QPushButton:checked { background-color: #005691; color: white; }
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
            if item == "Riwayat METAR":
                btn.setChecked(True)

        sidebar_layout.addStretch()

        self.logout_btn = QPushButton("LOGOUT")
        self.logout_btn.setObjectName("LogoutBtn")
        sidebar_layout.addWidget(self.logout_btn)
        body_layout.addWidget(sidebar)
        self.logout_btn.clicked.connect(self.proses_logout)

        # --- CONTENT AREA ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(15)

        # Judul Halaman Utama (Sesuai Gambar)
        page_title = QLabel("Riwayat Pengisian Data")
        page_title.setFont(QFont("Arial", 16, QFont.Bold))
        page_title.setStyleSheet("color: #000000;")
        content_layout.addWidget(page_title)

        # ==========================================
        # NEW: FILTER SEARCH BOX AREA (Sesuai Gambar)
        # ==========================================
        filter_card = QFrame()
        filter_card.setStyleSheet("""
            QFrame {
                background-color: #EBF2F7;
                border-radius: 8px;
                border: none;
            }
            QLabel {
                color: #333333;
                font-weight: bold;
                font-size: 11px;
                background: transparent;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                color: black;
            }
            QComboBox {
                background-color: white;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                color: black;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #0070C0;
                selection-color: white;
                outline: none;
            }
            QDateEdit {
                background-color: white;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                color: black;
            }
            QDateEdit QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #0070C0;
                selection-color: white;
            }
            QCalendarWidget QWidget {
                background-color: white;
                color: black;
            }
            QCalendarWidget QToolButton {
                color: black;
                background-color: white;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: black;
                background-color: white;
                selection-background-color: #0070C0;
                selection-color: white;
            }
            QCheckBox {
                color: #333333;
                font-size: 11px;
                background: transparent;
            }
            QPushButton {
                background-color: #0070C0;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
            }
            QPushButton:hover { background-color: #005691; }
        """)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        filter_layout.setSpacing(15)

        # Dropdown Nama Observer
        obs_box = QVBoxLayout()
        obs_box.addWidget(QLabel("Nama Observer"))
        self.input_filter_observer = QComboBox()
        self.input_filter_observer.addItem("Semua Observer", None)
        obs_box.addWidget(self.input_filter_observer)
        filter_layout.addLayout(obs_box, 40)

        # Date Picker Tanggal Pengisian
        date_box = QVBoxLayout()
        date_header = QHBoxLayout()
        date_header.addWidget(QLabel("Tanggal Pengisian"))
        self.chk_filter_tanggal = QCheckBox("Aktifkan")
        self.chk_filter_tanggal.setChecked(False)
        date_header.addWidget(self.chk_filter_tanggal)
        date_header.addStretch()
        date_box.addLayout(date_header)

        self.input_filter_tanggal = QDateEdit()
        self.input_filter_tanggal.setCalendarPopup(True)
        self.input_filter_tanggal.setDisplayFormat("yyyy-MM-dd")
        self.input_filter_tanggal.setDate(QDate.currentDate())
        self.input_filter_tanggal.setEnabled(False)
        self.chk_filter_tanggal.toggled.connect(self.input_filter_tanggal.setEnabled)
        date_box.addWidget(self.input_filter_tanggal)
        filter_layout.addLayout(date_box, 40)

        # Tombol Cari Rata Bawah
        btn_box = QVBoxLayout()
        btn_box.addWidget(QLabel("")) # Spacer tulisan atas kosong
        self.btn_cari = QPushButton("CARI")
        btn_box.addWidget(self.btn_cari)
        filter_layout.addLayout(btn_box, 20)

        content_layout.addWidget(filter_card)

        # Sub-header Tabel
        table_title = QLabel("Tabel Data Metar")
        table_title.setFont(QFont("Arial", 11, QFont.Bold))
        table_title.setStyleSheet("color: #000000; margin-top: 5px;")
        content_layout.addWidget(table_title)

        # ==========================================
        # 3. TABEL 4 KOLOM BARU (Sesuai Gambar)
        # ==========================================
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4) # Diubah menjadi 4 kolom utama
        self.table_widget.setHorizontalHeaderLabels([
            "Waktu pengisian", "Data yang diambil", "Observer", "Status"
        ])
        
        self.table_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setFocusPolicy(Qt.NoFocus)
        self.table_widget.setAlternatingRowColors(True)
        
        # Tetap mempertahankan skema warna lama (Putih & Bersih)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                gridline-color: #E0E0E0;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                selection-background-color: transparent;
                selection-color: #000000;
            }
            QTableWidget::item:alternate { background-color: #F9F9F9; }
            QTableWidget::item { color: #000000; font-weight: normal; font-size: 12px; padding-left: 10px; }
            QTableWidget::item:focus { background-color: transparent; border: none; }
            QHeaderView::section {
                background-color: #F0F4F8; color: #000000; font-weight: bold; font-size: 12px;
                padding: 10px; border: none; border-bottom: 2px solid #D0D0D0;
            }
        """)

        # Konfigurasi rasio kolom agar data METAR yang panjang mendapatkan ruang lega
        header_view = self.table_widget.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Waktu Pengisian
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)     # Data yang diambil (Teks Panjang)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Observer
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # Aksi

        self.table_widget.setColumnWidth(0, 180)
        self.table_widget.setColumnWidth(2, 160)
        self.table_widget.setColumnWidth(3, 140)
        
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setRowCount(0)

        content_layout.addWidget(self.table_widget)
        body_layout.addWidget(content_container)
        main_layout.addLayout(body_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.menu_group.idClicked.connect(self.handle_menu_click)
        self.btn_cari.clicked.connect(self.cari_riwayat)

        self.populate_observer_filter()
        self.load_riwayat()

    def populate_observer_filter(self):
        """Isi dropdown Nama Observer dengan daftar observer unik dari riwayat."""
        import sqlite3
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT u.nama
            FROM AutoFill_History h
            JOIN Users u ON h.id_user = u.id_user
            ORDER BY u.nama ASC
        """)
        observers = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.input_filter_observer.blockSignals(True)
        self.input_filter_observer.clear()
        self.input_filter_observer.addItem("Semua Observer", None)
        for nama in observers:
            self.input_filter_observer.addItem(nama, nama)
        self.input_filter_observer.blockSignals(False)

    def cari_riwayat(self):
        """Dipanggil saat tombol CARI diklik. Terapkan filter Observer & Tanggal."""
        observer_filter = self.input_filter_observer.currentData()
        tanggal_filter = None
        if self.chk_filter_tanggal.isChecked():
            tanggal_filter = self.input_filter_tanggal.date().toString("yyyy-MM-dd")

        self.load_riwayat(observer_filter=observer_filter, tanggal_filter=tanggal_filter)

    def load_riwayat(self, observer_filter=None, tanggal_filter=None):
        import sqlite3
        db_path = get_db_path() # Pastikan path database benar
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query JOIN untuk mengambil semua informasi yang diperlukan
        query = """
            SELECT 
                h.waktu_send, 
                COALESCE(m.raw_metar, 'Data METAR tidak ditemukan'), 
                u.nama, 
                h.status 
            FROM AutoFill_History h
            LEFT JOIN Users u ON h.id_user = u.id_user
            LEFT JOIN METAR m ON h.id_metar = m.id_metar
        """

        conditions = []
        params = []

        if observer_filter:
            conditions.append("u.nama = ?")
            params.append(observer_filter)

        if tanggal_filter:
            # h.waktu_send disimpan dalam format 'YYYY-MM-DD HH:MM:SS'
            conditions.append("DATE(h.waktu_send) = ?")
            params.append(tanggal_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY h.waktu_send DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows and (observer_filter or tanggal_filter):
            QMessageBox.information(self, "Info", "Tidak ada data yang cocok dengan filter yang dipilih.")

        # Panggil fungsi populate yang sudah Anda buat
        self.populate_riwayat_data(rows)       

    def handle_menu_click(self, button_id):
        if button_id == 0:
            self.dashboard()
        # Jika Perbarui Sesi Login (Index 2) diklik
        elif button_id == 2:
            self.perbarui_sesi_login()

    def perbarui_sesi_login(self):
        # Ambil objek pengirim sinyal
        sender_obj = self.sender()
        
        if sender_obj is not None:
            from PySide6.QtWidgets import QButtonGroup, QPushButton
            # Jika pengirimnya adalah QButtonGroup, ambil tombol aktif di dalamnya
            if isinstance(sender_obj, QButtonGroup):
                active_btn = sender_obj.checkedButton()
                if active_btn is not None:
                    active_btn.setChecked(False)
            # Jika pengirimnya langsung QPushButton
            elif isinstance(sender_obj, QPushButton):
                sender_obj.setChecked(False)

        # Membuat popup dengan teks hitam tegas
        msg = QMessageBox(self)
        msg.setWindowTitle("Perbarui Sesi Login")
        msg.setIcon(QMessageBox.Information)
        msg.setText("Browser akan terbuka untuk login BMKGSatu.\n\n"
                    "Silakan login secara manual, lalu klik tombol 'Resume' pada "
                    "jendela Playwright Inspector agar sesi login tersimpan.")
        msg.setStyleSheet("QLabel { color: black; } QPushButton { color: black; }")
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
        msg.setStyleSheet("QLabel { color: black; } QPushButton { color: black; }")
        msg.exec()

    def dashboard(self):
        from form_dashboard import DashboardApp
        self.dashboard_window = DashboardApp(user_data=self.user_data)
        self.dashboard_window.show()
        self.close()

    def proses_logout(self):
        from login_page import LoginPage
        self.login_window = LoginPage()
        self.login_window.show()
        self.close() 

    # ========================================================
    # 4. FUNGSI PARSING DATA SQLITE KE STRUKTUR BARU
    # ========================================================
    def populate_riwayat_data(self, data_list):
        self.table_widget.setRowCount(len(data_list))
        
        for row_idx, row_data in enumerate(data_list):
            # 1. Kolom 0: Waktu pengisian (tetap)
            item0 = QTableWidgetItem(str(row_data[0]))
            self.table_widget.setItem(row_idx, 0, item0)
            
            # 2. Kolom 1: Data yang diambil (METAR MENTAH, belum diparsing)
            full_metar = str(row_data[1])

            # Jika teksnya terlalu panjang, potong hanya untuk tampilan kolom,
            # namun teks METAR mentah lengkap tetap tersedia lewat tooltip
            if len(full_metar) > 60:
                display_text = full_metar[:60] + "..."
            else:
                display_text = full_metar

            item1 = QTableWidgetItem(display_text)
            item1.setToolTip(full_metar)
            self.table_widget.setItem(row_idx, 1, item1)
            
            # 3. Kolom 2: Nama Observer
            item2 = QTableWidgetItem(str(row_data[2]))
            self.table_widget.setItem(row_idx, 2, item2)
            
            # 4. Kolom 3: Aksi / Status (Tombol)
            status_text = str(row_data[3])
            btn_status = QPushButton(status_text)
            btn_status.setStyleSheet("""
                QPushButton {
                    background-color: #0070C0; 
                    color: white; 
                    font-weight: bold; 
                    font-size: 11px;
                    border: none; 
                    border-radius: 4px; 
                    margin: 2px 10px; 
                    padding: 6px;
                }
                QPushButton:hover { background-color: #005691; }
            """)
            
            container_widget = QWidget()
            container_widget.setStyleSheet("background-color: transparent; border: none;")
            container_layout = QHBoxLayout(container_widget)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(btn_status)
            
            self.table_widget.setCellWidget(row_idx, 3, container_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RiwayatApp()
    window.show()
    sys.exit(app.exec())
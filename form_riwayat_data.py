import sys
import os
from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem, 
    QHeaderView, QButtonGroup, QAbstractItemView, QLineEdit
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFont

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

        menu_items = ["Dashboard", "Riwayat Pengisian", "Perbarui Sesi Login"]
        for idx, item in enumerate(menu_items):
            btn = QPushButton(item)
            btn.setCheckable(True)
            self.menu_group.addButton(btn, idx)
            sidebar_layout.addWidget(btn)
            if item == "Riwayat Pengisian":
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

        # Input Nama Observer
        obs_box = QVBoxLayout()
        obs_box.addWidget(QLabel("Nama Observer"))
        self.input_filter_observer = QLineEdit()
        obs_box.addWidget(self.input_filter_observer)
        filter_layout.addLayout(obs_box, 40)

        # Input Tanggal Pengisian
        date_box = QVBoxLayout()
        date_box.addWidget(QLabel("Tanggal Pengisian"))
        self.input_filter_tanggal = QLineEdit()
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
            "Waktu pengisian", "Data yang diambil", "Observer", "Aksi"
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

    def handle_menu_click(self, button_id):
        if button_id == 0:
            self.dashboard()

    def dashboard(self):
        from form_dashboard import DashboardApp
        self.dashboard_window = DashboardApp()
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
        """
        Panggil fungsi ini saat membaca dari database SQLite.
        Format data_list: [ ["27 Juli 2026 17:00", "05/06/2026 04:30:00Z", "Bagas Eka S", "SUKSES"], ... ]
        """
        self.table_widget.setRowCount(len(data_list))
        
        for row_idx, row_data in enumerate(data_list):
            # 1. Mengisi 3 kolom data tekstual pertama
            for col_idx in range(3):
                item = QTableWidgetItem(str(row_data[col_idx]))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table_widget.setItem(row_idx, col_idx, item)
            
            # 2. Mengisi Kolom ke-4 (Aksi / Status Pengiriman) dengan Tombol SUKSES Biru Teks Putih serasi
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
            
            # Kontainer transparan untuk mempertahankan estetika baris putih polos
            container_widget = QWidget()
            container_widget.setStyleSheet("background-color: transparent; border: none;")
            container_layout = QHBoxLayout(container_widget)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(btn_status)
            
            # Pasang di kolom indeks ke-3 (Aksi)
            self.table_widget.setCellWidget(row_idx, 3, container_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RiwayatApp()
    window.show()
    sys.exit(app.exec())
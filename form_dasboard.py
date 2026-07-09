import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QGridLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QButtonGroup, QAbstractItemView
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QFont

class DashboardApp(QMainWindow):
    def __init__(self):
        super().__init__()
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

        # Logo BMKG dengan Deteksi Path Absolut (Anti-Bulat Biru)
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
        user_name = QLabel("Zenita Endriani")
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

        # --- SIDEBAR (Serasi dengan Form Input) ---
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
                btn.setChecked(True)

        sidebar_layout.addStretch()

        logout_btn = QPushButton("LOGOUT")
        logout_btn.setObjectName("LogoutBtn")
        sidebar_layout.addWidget(logout_btn)
        body_layout.addWidget(sidebar)

        # --- DASHBOARD CONTENT MAIN AREA ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(20)

        # Judul Utama Dashboard
        dashboard_title = QLabel("Dashboard Observer")
        dashboard_title.setFont(QFont("Arial", 16, QFont.Bold))
        dashboard_title.setStyleSheet("color: #000000;")
        content_layout.addWidget(dashboard_title)

        # ==========================================
        # 3. CARD CARDS INFO SECTION (Top 3 Boxes)
        # ==========================================
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        # Card 1: Data Terakhir (Hijau)
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

        # Card 2: Status Otomasi (Cokelat Emas)
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

        # Card 3: Jumlah Data (Biru Muda Pastel)
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

        # ==========================================
        # 4. TABEL DATA METAR SECTION
        # ==========================================
        # Header Tabel + Tombol Ambil Data Baru
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

        # Konstruksi QTableWidget
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(8)
        self.table_widget.setHorizontalHeaderLabels([
            "Waktu", "Arah Angin", "Kecepatan", "Visibility", "tinggi awan", "Temp", "Embun", "Aksi"
        ])
        
        # MENONAKTIFKAN SELEKSI AGAR TIDAK ADA EFEK SAAT DITEKAN
        self.table_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setFocusPolicy(Qt.NoFocus)
        # Mengaktifkan warna baris selang-seling (Opsional, jika ingin polos putih semua set ke False)
        self.table_widget.setAlternatingRowColors(True)
        
        #STYLING TABEL AGAR TIDAK ADA WARNA BIRU SAAT SELEKSI
        self.table_widget.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF; /* Warna dasar baris ganjil (Putih) */
                gridline-color: #E0E0E0;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                selection-background-color: transparent;
                selection-color: #000000;
            }
            
            /* PERBAIKAN UTAMA: Cara resmi Qt untuk mengatur baris selang-seling */
            QTableWidget::item:alternate {
                background-color: #F9F9F9; /* Warna baris genap (Abu-abu sangat tipis) */
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
            
        # Mengatur agar lebar kolom menyesuaikan porsi layar dengan rapi
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.verticalHeader().setVisible(False)

        self.table_widget.setRowCount(3)  

        content_layout.addWidget(self.table_widget)
            
        # PERBAIKAN TOMBOL: Polos tanpa background biru di sel, hanya tombol yang berwarna
        for row_idx in range(3):
            # Buat tombol "Proses & Preview" baru untuk baris aktif (row_idx)
            btn_proses = QPushButton("Proses & Preview")
            btn_proses.setStyleSheet("""
                QPushButton {
                    background-color: #0070C0; /* Background Biru */
                    color: white; /* Tulisan Putih */
                    font-weight: bold;
                    font-size: 11px;
                    border: none;
                    border-radius: 4px;
                    margin: 2px 10px;
                    padding: 6px;
                }
                QPushButton:hover { background-color: #005691; }
            """)
            
            # Wadah transparan agar efek seleksi biru bawaan Qt tidak muncul
            container_widget = QWidget()
            container_widget.setStyleSheet("background-color: transparent; border: none;")
            container_layout = QHBoxLayout(container_widget)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(btn_proses)
            
            # Pasang container tombol ke kolom nomor 7 (Aksi) pada baris ke-row_idx
            self.table_widget.setCellWidget(row_idx, 7, container_widget)
        
        content_layout.addWidget(self.table_widget)        
        body_layout.addWidget(content_container)
        main_layout.addLayout(body_layout)

        # Set Central Widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardApp()
    window.show()
    sys.exit(app.exec())
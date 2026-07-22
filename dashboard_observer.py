import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("METARFill - Dashboard")
        self.resize(1100, 750)
        self.setStyleSheet("background-color: #EDF0F2;")

        # Layout Utama
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("background-color: #4A76C0; color: white;")
        header.setFixedHeight(100)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 10, 20, 10)
        
        # Integrasi Logo
        self.logo_label = QLabel()
        pixmap = QPixmap("logo-bmkg.png") 
        scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label.setPixmap(scaled_pixmap)
        h_layout.addWidget(self.logo_label)
        
        stasiun_label = QLabel("STASIUN METEOROLOGI KELAS III\nDHOHO KEDIRI")
        stasiun_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        h_layout.addWidget(stasiun_label)
        h_layout.addStretch() 

        user_label = QLabel("Zenita Endriani    👤")
        user_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        h_layout.addWidget(user_label)
        main_layout.addWidget(header)

        # BODY (Sidebar + Konten)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(0)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setStyleSheet("background-color: #F0F0F0; border-right: 1px solid #ccc;")
        sidebar.setFixedWidth(260)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(20, 40, 20, 40)
        s_layout.setSpacing(20)
        
        self.sidebar_buttons = []
        for text in ["Dashboard", "Riwayat METAR", "Perbarui Sesi Login"]:
            btn = QPushButton(text)
            btn.setCheckable(True) 
            btn.setAutoExclusive(True) 
            
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left; 
                    border: none; 
                    font-weight: bold; 
                    font-size: 18px; 
                    padding: 10px; 
                    color: black;
                }
                QPushButton:checked {
                    background-color: #4A76C0; /* Warna Biru saat diklik */
                    color: white;             /* Warna teks putih saat diklik */
                    border-radius: 5px;
                }
            """)
            s_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)
        
        s_layout.addStretch()
        logout = QPushButton("LOGOUT")
        logout.setStyleSheet("text-align: left; border: none; font-weight: bold; font-size: 18px; color: black;")
        s_layout.addWidget(logout)
        body_layout.addWidget(sidebar)

        # Main Content
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(30, 30, 30, 30)
        c_layout.setSpacing(20)
        
        title_label = QLabel("Dashboard Observer")
        title_label.setStyleSheet("color: black; font-size: 28px; font-weight: bold;")
        c_layout.addWidget(title_label)
        
        # Stats Cards
        stats_layout = QHBoxLayout()
        for label, color in [("Data Terakhir\n01:30", "#6A9D6F"), ("Status Otomasi\nSukses", "#B59458"), ("Jumlah Data\n48", "#80A6B7")]:
            card = QLabel(label)
            card.setStyleSheet(f"background-color: {color}; color: white; border-radius: 8px; font-weight: bold; padding: 20px;")
            card.setAlignment(Qt.AlignCenter)
            stats_layout.addWidget(card)
        c_layout.addLayout(stats_layout)

        # Tombol
        btn_ambil = QPushButton("Ambil Data Baru")
        btn_ambil.setStyleSheet("background-color: #4F46E5; color: white; padding: 10px; border-radius: 4px;")
        btn_ambil.setFixedWidth(150)
        c_layout.addWidget(btn_ambil, alignment=Qt.AlignRight)

        # Tabel
        table = QTableWidget(3, 7)
        table.setHorizontalHeaderLabels(["Waktu", "Arah Angin", "Kecepatan", "Visibility", "tingi awan", "Temp", "Aksi"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        c_layout.addWidget(table)
        table.setStyleSheet("""
            QTableWidget { background-color: #C0C0C0; gridline-color: #A0A0A0; }
            QHeaderView::section { background-color: #808080; color: white; padding: 5px; font-weight: bold; }
            QTableWidget::item { color: black; }
        """)

        body_layout.addWidget(content)
        main_layout.addLayout(body_layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardPage()
    window.show()
    sys.exit(app.exec())
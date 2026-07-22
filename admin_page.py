# admin_page.py
import sys
import os
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QLineEdit, QComboBox, QMessageBox, QFrame, QAbstractItemView,
    QButtonGroup
)
from PySide6.QtGui import QFont, QPixmap

from auth_utils import hash_password, get_db_path


class UserModal(QDialog):
    """Jendela Pop-up (Modal) untuk Tambah/Edit Pengguna"""
    def __init__(self, title, parent=None, user_data=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(380, 340)

        # Sifat Modal: mengunci jendela utama di belakangnya
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.user_data = user_data  # dict {id_user, nama, role} kalau mode edit

        # Styling eksplisit: tanpa ini, teks ikut warna default OS (misalnya
        # putih saat OS memakai dark mode) sehingga tulisan jadi samar di
        # atas latar pop-up yang terang.
        self.setStyleSheet("""
            QDialog {
                background-color: #F0F4F8;
            }
            QLabel {
                color: #000000;
                background-color: transparent;
            }
            QLineEdit {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #A0A0A0;
                border-radius: 4px;
                padding: 6px;
                font-size: 13px;
            }
            QComboBox {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #A0A0A0;
                border-radius: 4px;
                padding: 4px;
                font-size: 13px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #000000;
                selection-background-color: #0077D4;
                selection-color: #FFFFFF;
            }
        """)

        # Layout Utama Pop-up
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 20, 30, 20)

        # Judul Form
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Input Nama
        layout.addWidget(QLabel("Nama Pengguna:"))
        self.entry_nama = QLineEdit()
        self.entry_nama.setPlaceholderText("Masukkan nama lengkap")
        layout.addWidget(self.entry_nama)

        # Input Password
        layout.addWidget(QLabel("Password:"))
        self.entry_pass = QLineEdit()
        self.entry_pass.setEchoMode(QLineEdit.EchoMode.Password)

        # Dropdown Role
        layout.addWidget(QLabel("Role Akses:"))
        self.combo_role = QComboBox()
        self.combo_role.addItems(["Admin", "Observer"])
        layout.addWidget(self.combo_role)

        # Jika Mode Edit, isi data yang sudah ada (kecuali password: password
        # tersimpan dalam bentuk hash sehingga tidak bisa/boleh ditampilkan
        # ulang; dikosongkan berarti "tidak diubah")
        if self.user_data:
            self.entry_nama.setText(self.user_data["nama"])
            self.combo_role.setCurrentText(self.user_data["role"])
            self.entry_pass.setPlaceholderText("Kosongkan jika tidak ingin mengubah password")
        else:
            self.entry_pass.setPlaceholderText("Masukkan password")

        layout.insertWidget(4, self.entry_pass)

        # Layout Tombol (Simpan & Batal)
        btn_layout = QHBoxLayout()
        self.btn_simpan = QPushButton("Simpan Data")
        self.btn_simpan.setStyleSheet("background-color: #0077D4; color: white; font-weight: bold; height: 30px;")
        self.btn_simpan.clicked.connect(self.accept)

        self.btn_batal = QPushButton("Batal")
        self.btn_batal.setStyleSheet("background-color: #7F8C8D; color: white; height: 30px;")
        self.btn_batal.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_simpan)
        btn_layout.addWidget(self.btn_batal)
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "nama": self.entry_nama.text().strip(),
            "pass": self.entry_pass.text().strip(),
            "role": self.combo_role.currentText()
        }


class AdminApp(QMainWindow):
    def __init__(self, user_data=None):
        super().__init__()
        # Data admin yang sedang login (dikirim dari LoginPage). Diberi nilai
        # default supaya file ini tetap bisa dijalankan mandiri untuk testing.
        self.user_data = user_data or {"id_user": None, "nama": "Zenita Endriani", "role": "Admin"}

        self.setWindowTitle("Halaman Pengguna (Admin) - BMKG Dhoho Kediri")
        self.resize(1100, 700)
        self.setStyleSheet("background-color: #F0F4F8; font-family: 'Segoe UI', Arial, sans-serif;")

        # Main Layout: Top Header + Bottom Content (mengikuti struktur form_dashboard.py)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================
        # 1. HEADER SECTION (Serasi dengan Dashboard)
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
        user_name = QLabel(self.user_data.get("nama", "Admin"))
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

        # --- SIDEBAR (style sama persis dengan form_dashboard.py) ---
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

        menu_items = ["Manajemen Pengguna"]
        for idx, item in enumerate(menu_items):
            btn = QPushButton(item)
            btn.setCheckable(True)
            self.menu_group.addButton(btn, idx)
            sidebar_layout.addWidget(btn)
            if item == "Manajemen Pengguna":
                btn.setChecked(True)

        sidebar_layout.addStretch()

        self.logout_btn = QPushButton("LOGOUT")
        self.logout_btn.setObjectName("LogoutBtn")
        self.logout_btn.clicked.connect(self.proses_logout)

        sidebar_layout.addWidget(self.logout_btn)
        body_layout.addWidget(sidebar)

        # --- CONTENT BODY (Tabel Manajemen Pengguna) ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(20)

        # Baris Judul + Tombol Tambah
        title_row = QHBoxLayout()
        content_title = QLabel("Manajemen Pengguna")
        content_title.setFont(QFont("Arial", 16, QFont.Bold))
        content_title.setStyleSheet("color: #000000;")

        self.add_user_btn = QPushButton("+ Tambah User Baru")
        self.add_user_btn.setStyleSheet("""
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
        self.add_user_btn.clicked.connect(lambda: self.open_modal("Tambah Pengguna"))

        title_row.addWidget(content_title)
        title_row.addStretch()
        title_row.addWidget(self.add_user_btn)
        content_layout.addLayout(title_row)

        # Tabel Data Pengguna (style sama seperti tabel di form_dashboard.py)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID User", "Nama", "Role", "Aksi"])
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(True)

        self.table.setStyleSheet("""
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
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)

        content_layout.addWidget(self.table)
        body_layout.addWidget(content_container)
        main_layout.addLayout(body_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.load_table_data()

    # ---------------------------------------------------------------
    # CRUD - terhubung langsung ke database_metar.db (tabel Users)
    # ---------------------------------------------------------------
    def get_connection(self):
        return sqlite3.connect(get_db_path())

    def fetch_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_user, nama, role FROM Users ORDER BY id_user")
        rows = cursor.fetchall()
        conn.close()
        return [{"id_user": r[0], "nama": r[1], "role": r[2]} for r in rows]

    def load_table_data(self):
        """Mengambil data terbaru dari database dan merender ke QTableWidget"""
        try:
            users = self.fetch_users()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Kesalahan Database", f"Gagal membaca data pengguna:\n{e}")
            return

        self.table.setRowCount(0)

        for row_idx, user in enumerate(users):
            self.table.insertRow(row_idx)

            fields = [str(user["id_user"]), user["nama"], user["role"]]
            for col_idx, text in enumerate(fields):
                item = QTableWidgetItem(text)
                if col_idx == 0:
                    item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                self.table.setItem(row_idx, col_idx, item)

            # Wadah Tombol Aksi (Edit & Delete) di dalam kolom terakhir
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(5)

            edit_btn = QPushButton("📝 Edit")
            edit_btn.setStyleSheet("background-color: #2ECC71; color: white; border-radius: 2px; font-size: 11px; font-weight: bold; height: 24px;")
            edit_btn.clicked.connect(lambda checked, u=user: self.open_modal("Edit Pengguna", u))

            del_btn = QPushButton("🗑 Delete")
            del_btn.setStyleSheet("background-color: #E74C3C; color: white; border-radius: 2px; font-size: 11px; font-weight: bold; height: 24px;")
            del_btn.clicked.connect(lambda checked, u=user: self.delete_user(u))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(del_btn)
            self.table.setCellWidget(row_idx, 3, action_widget)

    def open_modal(self, title, user_data=None):
        """Fungsi pembuka pop-up form Tambah/Edit, langsung menulis ke database"""
        dialog = UserModal(title, self, user_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            res = dialog.get_data()

            if not res["nama"] or (not user_data and not res["pass"]):
                QMessageBox.warning(self, "Peringatan", "Nama dan password wajib diisi!")
                return

            try:
                conn = self.get_connection()
                cursor = conn.cursor()

                if user_data:  # Mode Update
                    if res["pass"]:
                        cursor.execute(
                            "UPDATE Users SET nama = ?, password = ?, role = ? WHERE id_user = ?",
                            (res["nama"], hash_password(res["pass"]), res["role"], user_data["id_user"]),
                        )
                    else:
                        cursor.execute(
                            "UPDATE Users SET nama = ?, role = ? WHERE id_user = ?",
                            (res["nama"], res["role"], user_data["id_user"]),
                        )
                else:  # Mode Insert Baru
                    cursor.execute(
                        "INSERT INTO Users (nama, password, role) VALUES (?, ?, ?)",
                        (res["nama"], hash_password(res["pass"]), res["role"]),
                    )

                conn.commit()
                conn.close()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Peringatan", f"Nama pengguna '{res['nama']}' sudah digunakan!")
                return
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Kesalahan Database", f"Gagal menyimpan data:\n{e}")
                return

            self.load_table_data()  # Refresh tabel

    def delete_user(self, user):
        if self.user_data.get("id_user") == user["id_user"]:
            QMessageBox.warning(self, "Peringatan", "Tidak bisa menghapus akun yang sedang login!")
            return

        confirm = QMessageBox.question(
            self, "Konfirmasi", f"Hapus user #{user['id_user']} ({user['nama']})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Users WHERE id_user = ?", (user["id_user"],))
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Kesalahan Database", f"Gagal menghapus data:\n{e}")
                return
            self.load_table_data()

    def proses_logout(self):
        from login_page import LoginPage
        self.login_window = LoginPage()
        self.login_window.show()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdminApp()
    window.show()
    sys.exit(app.exec())
# session_worker.py
"""
Worker thread bersama untuk menjalankan save_session.save_auth() di
background, supaya jendela Qt (Dashboard / Riwayat / Form Input) tidak
"Not Responding" selama browser Playwright terbuka menunggu login manual.
"""

from PySide6.QtCore import QThread, Signal


class SessionUpdateWorker(QThread):
    # emit(sukses: bool, pesan: str) setelah proses selesai / gagal
    selesai = Signal(bool, str)

    def run(self):
        try:
            from save_session import save_auth
            save_auth()
            self.selesai.emit(
                True,
                "Sesi login berhasil diperbarui dan disimpan ke auth_state.json."
            )
        except Exception as e:
            self.selesai.emit(False, f"Gagal memperbarui sesi login:\n{e}")
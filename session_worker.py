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
from PySide6.QtCore import QThread, Signal

from fill_form2 import run_test


class KirimWorker(QThread):
    selesai = Signal()
    gagal = Signal(str)

    def __init__(self, data_cuaca, nama_observer, parent=None):
        super().__init__(parent)
        self.data_cuaca = data_cuaca
        self.nama_observer = nama_observer

    def run(self):
        try:
            run_test(self.data_cuaca, self.nama_observer)
            self.selesai.emit()
        except Exception as e:
            self.gagal.emit(str(e))
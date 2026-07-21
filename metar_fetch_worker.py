from PySide6.QtCore import QThread, Signal

from parser import proses_data_untuk_tanggal


class MetarFetchWorker(QThread):
    selesai = Signal(dict)

    gagal = Signal(str)

    def __init__(self, tahun, bulan, tanggal, parent=None):
        super().__init__(parent)
        self.tahun = tahun
        self.bulan = bulan
        self.tanggal = tanggal

    def run(self):
        try:
            ringkasan = proses_data_untuk_tanggal(self.tahun, self.bulan, self.tanggal)
            self.selesai.emit(ringkasan)
        except Exception as e:
            self.gagal.emit(str(e))
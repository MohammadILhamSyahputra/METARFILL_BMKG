from PySide6.QtCore import QThread, Signal

from parser import proses_data_untuk_tanggal


class MetarFetchWorker(QThread):
    """
    Worker thread untuk menjalankan proses_data_untuk_tanggal() (fetch web
    BMKG + parsing + simpan ke DB) di LUAR main/GUI thread.

    PENTING - kenapa ini dibuat:
    Sebelumnya form_dashboard.py memanggil proses_data_untuk_tanggal()
    LANGSUNG di main thread (di dalam ambil_data_tanggal()). Karena
    requests.get() di baliknya bisa menunggu sampai 30 detik (timeout),
    selama itu main thread -- termasuk event loop Qt -- berhenti total
    memproses event. Akibatnya:
      1. Window Dashboard tampak "hang"/tidak merespon. Ini paling parah
         saat aplikasi PERTAMA KALI dibuka, karena __init__ sebelumnya
         memanggil ambil_data_tanggal() secara sinkron SEBELUM window
         sempat tampil ke layar sama sekali (window baru benar-benar
         digambar setelah blok ini selesai) -- pengguna hanya melihat
         layar kosong/hang beberapa detik, seolah window tertutup/tidak
         terbuka.
      2. Messagebox loading ("Mengambil data...") ikut freeze; tombol
         close (X) di title bar-nya tidak berfungsi selama fetch
         berjalan karena event loop tidak sempat memproses klik itu,
         sehingga terkesan notifikasi tidak bisa ditutup.

    Dengan memindahkan proses_data_untuk_tanggal() ke QThread terpisah,
    main thread (dan event loop Qt-nya) tetap berjalan normal selama
    proses fetch berlangsung -- window & semua messagebox tetap
    responsif dan bisa ditutup kapan saja.
    """

    # Dipancarkan saat proses selesai TANPA error, membawa dict ringkasan
    # yang sebelumnya dikembalikan langsung oleh proses_data_untuk_tanggal().
    selesai = Signal(dict)

    # Dipancarkan kalau ada exception saat proses berjalan (mis. gagal
    # koneksi, error parsing tak terduga, dsb), membawa pesan error-nya.
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
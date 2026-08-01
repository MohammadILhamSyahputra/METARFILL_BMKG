# fill_form.py
import os
import time
import threading
import queue
from playwright.sync_api import sync_playwright


# =============================================================================
# HELPER: Isi salah satu grup radio button di modal "Cuaca Saat Pengamatan"
# =============================================================================
def isi_radio_group(container, name_radio, value):
    """
    name_radio contoh: 'radio-intensity', 'radio-descriptor', 'radio-precipitation',
                        'radio-obscuration', 'radio-other'
    value      contoh: '', '-', '+', 'VC', 'TS', 'RA', dst (sesuai atribut value di HTML)

    Jika value bernilai None, grup ini dilewati (tidak disentuh sama sekali).
    Jika value == "" (string kosong), tetap dianggap pilihan valid (mis. intensity
    "Moderate" atau descriptor "None" yang value HTML-nya memang kosong).
    """
    if value is None:
        return

    radio = container.locator(f"input[name='{name_radio}'][value='{value}']")
    if radio.count() > 0:
        radio.check(force=True)
        print(f"   -> '{name_radio}' diset ke '{value}'")
    else:
        print(f"   -> WARNING: value '{value}' tidak ditemukan untuk radio '{name_radio}'")


# =============================================================================
# HELPER: Tutup modal Cuaca Saat Pengamatan setelah selesai memilih
# =============================================================================
def tutup_modal_cuaca(page):
    """
    HTML yang diberikan tidak menyertakan tombol submit/close modal secara eksplisit,
    jadi di sini dicoba beberapa selector umum untuk modal BootstrapVue.
    """
    kemungkinan_teks = ["OK", "Simpan", "Submit", "Tutup", "Selesai"]
    for teks in kemungkinan_teks:
        tombol = page.locator(f".modal-footer button:has-text('{teks}')")
        if tombol.count() > 0:
            tombol.first.click()
            print(f"-> Modal cuaca ditutup lewat tombol '{teks}'.")
            return
    # Fallback: tekan Escape kalau tidak ada tombol yang cocok
    page.keyboard.press("Escape")
    print("-> Modal cuaca ditutup lewat tombol Escape.")


def run_test(data_cuaca, nama_observer, event_selesai_manual=None):
    """
    event_selesai_manual (opsional): threading.Event yang di-set() dari LUAR
    (tombol "Selesai" di GUI aplikasi) untuk memberi tahu fungsi ini bahwa
    observer sudah selesai, TANPA bergantung pada sinyal dari browser
    (page.close/context.close/browser.disconnected/is_connected()). Ini jalur
    paling andal, karena menutup window Chromium secara manual terbukti tidak
    selalu mengirim sinyal apapun ke Playwright.

    Catatan penting soal kecepatan respons:

    Playwright's `with sync_playwright() as p:` menutup koneksi ke driver
    (p.stop()) begitu blok `with` selesai. Kalau browser sudah mati mendadak
    (observer close manual, atau proses/OS yang membunuhnya), handshake
    penutupan itu bisa menggantung puluhan detik sebelum akhirnya timeout.

    Supaya observer TIDAK ikut menunggu itu, seluruh proses Playwright
    (buka browser -> isi form -> tunggu browser ditutup) dijalankan di
    THREAD TERPISAH (`_worker_playwright`). Begitu browser terdeteksi
    tertutup, thread itu langsung lapor sukses/gagal lewat `hasil_queue`,
    dan `run_test()` langsung `return`/`raise` saat itu juga (maksimal
    ~1 detik, bukan menunggu 60 detik). Proses cleanup Playwright yang
    lambat (p.stop()) tetap jalan di background, tidak memblokir apa pun.
    """
    hasil_queue = queue.Queue()
    sudah_lapor = threading.Event()

    def _lapor_sukses():
        if not sudah_lapor.is_set():
            sudah_lapor.set()
            hasil_queue.put(("sukses", None))

    def _lapor_gagal(pesan):
        if not sudah_lapor.is_set():
            sudah_lapor.set()
            hasil_queue.put(("gagal", pesan))

    def _worker_playwright():
        with sync_playwright() as p:
            browser = None
            ditutup_manual = threading.Event()

            try:
                browser = p.chromium.launch(headless=False)
                # 'disconnected' baru terpicu setelah SELURUH proses browser mati total,
                # ini bisa lambat. Tambahkan juga listener di context & page yang
                # terpicu jauh lebih cepat begitu window/tab ditutup oleh observer.
                browser.on("disconnected", lambda: ditutup_manual.set())

                context = browser.new_context(storage_state="auth_state.json")
                context.on("close", lambda: ditutup_manual.set())

                page = context.new_page()
                page.on("close", lambda _: ditutup_manual.set())
                page.set_default_timeout(60000)

                # PENTING: begitu observer menutup window secara manual (klik X),
                # banyak web form (kemungkinan termasuk BMKGSatu) punya listener
                # 'beforeunload' yang memicu dialog konfirmasi native "Leave site?".
                # Selama dialog itu belum dijawab, browser TIDAK benar-benar
                # tertutup -> event 'disconnected'/'close' juga ikut nyangkut,
                # itulah gap lama yang cuma muncul di penutupan manual (bukan
                # penutupan otomatis lewat browser.close() kita sendiri, yang
                # memang bypass dialog semacam ini). Auto-accept semua dialog
                # supaya window langsung benar-benar tertutup tanpa menunggu.
                page.on("dialog", lambda dialog: dialog.accept())

                print("Membuka halaman form...")
                url = "https://bmkgsatu.bmkg.go.id/meteorologi/metarspeci"
                page.goto(url, wait_until="commit")

                # =========================================================
                # 1. URUTAN 1: ISI WMO ID
                # =========================================================
                print("\n[1] Mengisi WMO ID...")
                wmo_target = "96929"
                wmo_container = page.locator("div.form-group:has(label:has-text('WMO ID'))")
                wmo_search = wmo_container.locator(".vs__search")

                wmo_search.click()
                wmo_search.fill(wmo_target)

                wmo_option = wmo_container.locator(f"ul[role='listbox'] li:has-text('{wmo_target}')")
                wmo_option.wait_for(state="visible")
                wmo_option.click()
                print("-> WMO ID Berhasil dipilih!")

                # Tunggu indikator loading bawaan stasiun selesai
                page.wait_for_selector(".vs__spinner", state="hidden")
                time.sleep(2)

                # =========================================================
                # 2. URUTAN 2: ISI NAMA OBSERVER
                # =========================================================
                print("\n[2] Mengisi Nama Observer...")
                observer_container = page.locator("div.form-group:has(label:has-text('Nama Observer'))")

                observer_search = observer_container.locator(".vs__search")

                observer_search.click()
                observer_search.fill("")  # Bersihkan dulu
                observer_search.fill(nama_observer)

                observer_option = observer_container.locator("ul[role='listbox'] li")
                observer_option.first.wait_for(state="visible", timeout=10000)

                target_option = observer_container.locator(f"ul[role='listbox'] li:has-text('{nama_observer}')")

                if target_option.count() > 0:
                    target_option.click()
                    print(f"-> Nama Observer '{nama_observer}' Berhasil dipilih!")
                else:
                    print(f"-> ERROR: Nama '{nama_observer}' tidak ditemukan di list!")

                time.sleep(1)

                # =========================================================
                # 3. URUTAN 3: ISI FIELD TYPE (METAR/SPECI)
                # =========================================================
                print("\n[3] Mengisi Field Type...")
                page.wait_for_selector("select[data-v-09a7bfae]#input-type")
                type_target = "METAR"
                page.select_option("select[data-v-09a7bfae]#input-type", value=type_target)
                print(f"-> Field Type Berhasil diubah ke '{type_target}'!")

                time.sleep(1)

                # =========================================================
                # 4. URUTAN 4: VERIFIKASI FIELD ICAO
                # =========================================================
                print("\n[4] Memeriksa nilai otomatis ICAO...")
                page.wait_for_selector("#input-icao")
                nilai_icao = page.locator("#input-icao").input_value()
                print(f"-> Kode ICAO otomatis terisi: '{nilai_icao}'")

                # =========================================================
                # [*] KELOMPOK DROPDOWN: TREND
                # =========================================================
                print("\n[*] Mengisi Trend...")
                target_trend = "NOSIG"
                page.wait_for_selector("select[data-v-1010a25b]#input-type", state="attached")
                page.evaluate(f"""() => {{
                    const trendSelect = document.querySelector('select[data-v-1010a25b]#input-type');
                    if (trendSelect) {{
                        trendSelect.value = '{target_trend}';
                        trendSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        trendSelect.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}""")
                print(f"-> Trend Berhasil dipaksa set ke '{target_trend}'!")

                # 🛑 TUNGGU SELURUH PROSES FETCHING / RESET DARI WEB SELESAI TOTAL 🛑
                print("Menunggu web selesai mengambil data cuaca & mereset form...")
                page.wait_for_selector(".vs__spinner", state="hidden")
                time.sleep(3)

                # =========================================================
                # 5. URUTAN 5: ISI TANGGAL (SETELAH RESET WEB SELESAI)
                # =========================================================
                raw_date = data_cuaca.get('full_date', '')

                if raw_date and "-" in raw_date:
                    thn, bln, tgl = raw_date.split("-")
                    iso_date = f"{thn}-{bln.zfill(2)}-{tgl.zfill(2)}"
                else:
                    iso_date = raw_date

                print(f"\n[5] Mengisi Tanggal Filter: {iso_date}...")

                dp_input = page.locator("#datepicker")
                dp_input.click()
                time.sleep(0.5)

                # Paksa kalender render bulan target
                page.evaluate(f"""(targetIso) => {{
                    const input = document.querySelector('#datepicker');
                    if (input) {{
                        const wrapper = input.closest('.b-form-datepicker') || input.parentElement;
                        const vm = wrapper ? wrapper.__vue__ : null;
                        if (vm && 'activeYMD' in vm) {{
                            vm.activeYMD = targetIso; 
                        }}
                    }}
                }}""", iso_date)
                time.sleep(0.5)

                # Klik cell tanggal pada popup kalender
                target_cell = page.locator(f"[data-date='{iso_date}']").first
                if target_cell.count() > 0:
                    target_cell.click(force=True)
                    print(f"-> Berhasil mengklik tanggal {iso_date} dari kalender!")
                else:
                    print(f"-> Fallback: Menyuntikkan tanggal {iso_date} via JS.")
                    page.evaluate(f"""(targetIso) => {{
                        const input = document.querySelector('#datepicker');
                        if (input) {{
                            const wrapper = input.closest('.b-form-datepicker') || input.parentElement;
                            const vm = input.__vue__ || (wrapper ? wrapper.__vue__ : null);
                            if (vm) {{
                                if ('selectedYMD' in vm) vm.selectedYMD = targetIso;
                                if ('value' in vm) vm.value = targetIso;
                                if (typeof vm.$emit === 'function') vm.$emit('input', targetIso);
                            }}
                        }}
                    }}""", iso_date)

                time.sleep(1.5)  # Beri jeda kecil setelah ubah tanggal

                # =========================================================
                # 6 & 7. URUTAN 6 & 7: ISI JAM & MENIT
                # =========================================================
                print(f"\n[6 & 7] Mengisi Jam: {data_cuaca['hour']}, Menit: {data_cuaca['minute']}...")

                page.wait_for_selector("#input-jam")
                page.select_option("#input-jam", value=data_cuaca['hour'])

                page.wait_for_selector("#input-menit")
                page.select_option("#input-menit", value=data_cuaca['minute'])
                print(f"-> Waktu berhasil diset ke {data_cuaca['hour']}:{data_cuaca['minute']}")

                print("\n[!] Menunggu sinkronisasi server akibat perubahan tanggal/waktu...")
                time.sleep(1.5)

                try:
                    # Tunggu sampai animasi loading web benar-benar hilang (maks 15 detik)
                    page.wait_for_selector(".vs__spinner", state="hidden", timeout=15000)
                except Exception:
                    pass
                time.sleep(2)

                # =========================================================
                # 8. URUTAN 8: SINKRONISASI DATA ANGIN, VISIBILITY, SUHU, TEKANAN
                # =========================================================
                print(f"\n[8] Menginjeksi data angin/visibility/suhu/tekanan: {data_cuaca}")
                page.evaluate("""(data) => {
                    const triggerEvent = (el) => {
                        if (el) {
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    };

                    const mapping = {
                        'winds-direction': data.direction,
                        'wind_speed': data.speed,
                        'wind_gust': data.gust,
                        'winds-wd-dn': data.dir_min,
                        'winds-wd-dx': data.dir_max,
                        'input-prevailing': data.visibility,
                        'v-air-temp': data.temp,
                        'v-dew-point': data.dew_point,
                        'v-presure': data.pressure
                    };

                    for (const [id, value] of Object.entries(mapping)) {
                        if (value === undefined || value === null || value === '') continue;
                        const el = document.getElementById(id);
                        if (el) {
                            el.value = value;
                            triggerEvent(el);
                        }
                    }
                }""", data_cuaca)
                print("-> Injeksi data angin/visibility/suhu/tekanan selesai.")

                time.sleep(1)

                # =========================================================
                # 9. URUTAN 9: CHECKBOX VRB
                # =========================================================
                print("\n[9] Mengatur kondisi VRB...")
                vrb_harus_dicentang = bool(data_cuaca.get('is_vrb', False))

                def _set_checkbox_vrb(target: bool):
                    checkbox = page.locator("#checkbox-vrb")
                    if checkbox.count() == 0:
                        return {"found": False, "checked": None}

                    status_sekarang = checkbox.is_checked()
                    if status_sekarang != target:
                        checkbox.click(force=True)
                        page.wait_for_timeout(300)

                    return {"found": True, "checked": checkbox.is_checked()}

                hasil_vrb = _set_checkbox_vrb(vrb_harus_dicentang)
                if hasil_vrb.get('found') and hasil_vrb.get('checked') == vrb_harus_dicentang:
                    print(f"-> Checkbox VRB berhasil diset ke {vrb_harus_dicentang}.")

                time.sleep(1)

                # =========================================================
                # 9b. URUTAN 9b: CHECKBOX STATUS LAPORAN (COR / NIL / AUTO)
                # =========================================================
                print("\n[9b] Mengatur checkbox status laporan (COR/NIL/AUTO)...")

                def _centang_checkbox_status(elemen_id, aktif, label):
                    if not aktif:
                        return
                    checkbox = page.locator(f"#{elemen_id}")
                    if checkbox.count() > 0 and not checkbox.is_checked():
                        checkbox.click(force=True)
                        page.wait_for_timeout(300)
                        print(f"   -> Checkbox '{label}' dicentang.")

                _centang_checkbox_status("checkbox-cor", data_cuaca.get("is_cor"), "COR")
                _centang_checkbox_status("checkbox-nil", data_cuaca.get("is_nil"), "NIL")
                _centang_checkbox_status("checkbox-auto", data_cuaca.get("is_auto"), "AUTO")

                time.sleep(1)

                # =========================================================
                # 10. URUTAN 10: BLOK CUACA SAAT PENGAMATAN (MODAL)
                # =========================================================
                print("\n[10] Mengisi Blok Cuaca Saat Pengamatan...")
                ada_data_cuaca_saat_ini = any(
                    data_cuaca.get(k) is not None
                    for k in ("weather_intensity", "weather_descriptor",
                              "weather_precipitation", "weather_obscuration", "weather_other")
                )

                if ada_data_cuaca_saat_ini:
                    tombol_cuaca = page.locator("button.button-weather:not([disabled])").first
                    if tombol_cuaca.count() > 0:
                        tombol_cuaca.click()
                        page.wait_for_selector("div[id*='__BVID__'][id*='modal_body']", state="visible")
                        modal = page.locator("div[id*='__BVID__'][id*='modal_body']")

                        isi_radio_group(modal, "radio-intensity", data_cuaca.get("weather_intensity"))
                        isi_radio_group(modal, "radio-descriptor", data_cuaca.get("weather_descriptor"))
                        isi_radio_group(modal, "radio-precipitation", data_cuaca.get("weather_precipitation"))
                        isi_radio_group(modal, "radio-obscuration", data_cuaca.get("weather_obscuration"))
                        isi_radio_group(modal, "radio-other", data_cuaca.get("weather_other"))

                        tutup_modal_cuaca(page)
                    time.sleep(1)

                # =========================================================
                # 11. URUTAN 11: BLOK CUACA YANG LALU
                # =========================================================
                recent_weather = data_cuaca.get("recent_weather")
                if recent_weather is not None:
                    print(f"\n[11] Mengisi Cuaca yang Lalu: '{recent_weather}'...")
                    page.wait_for_selector("#recent-w-1")
                    page.select_option("#recent-w-1", value=recent_weather)

                time.sleep(1)

                # =========================================================
                # 12. URUTAN 12: BLOK AWAN (MAKSIMAL 3 RECORD)
                # =========================================================
                daftar_awan = data_cuaca.get("clouds", [])[:3]
                print(f"\n[12] Mengisi Blok Awan ({len(daftar_awan)} record)...")

                for idx, awan in enumerate(daftar_awan, start=1):
                    print(f"   -> Record awan #{idx}: {awan}")

                    page.wait_for_selector("#clouds-jumlah")
                    if awan.get("amount"):
                        page.select_option("#clouds-jumlah", value=awan["amount"])

                    page.wait_for_selector("#cloud_height")
                    if awan.get("height"):
                        tinggi_awan = str(int(awan["height"]))
                        page.fill("#cloud_height", tinggi_awan)

                    page.wait_for_selector("#select-type")
                    if awan.get("type"):
                        page.select_option("#select-type", value=awan["type"])
                    else:
                        page.select_option("#select-type", index=0)

                    time.sleep(1)

                    tabel_awan = page.locator("table:has(#clouds-jumlah)")
                    jumlah_baris_sebelum = tabel_awan.locator("tbody tr").count()

                    tombol_tambah = tabel_awan.locator("button.btn-success:has(svg.feather-plus)").first
                    tombol_tambah.scroll_into_view_if_needed()
                    is_disabled = tombol_tambah.evaluate("(btn) => btn.disabled || btn.classList.contains('disabled')")

                    if not is_disabled:
                        tombol_tambah.click()
                    else:
                        tombol_tambah.evaluate("""(btn) => {
                            btn.disabled = false;
                            btn.removeAttribute('disabled');
                            btn.classList.remove('disabled');
                            btn.dispatchEvent(new MouseEvent('click', { view: window, bubbles: true, cancelable: true }));
                        }""")

                    time.sleep(1)

                # =========================================================
                # 9c. RE-VERIFIKASI CHECKBOX VRB SEBELUM SUBMIT
                # =========================================================
                print("\n[9c] Memastikan ulang status checkbox VRB sebelum submit...")
                _set_checkbox_vrb(vrb_harus_dicentang)

                print("-> Injeksi data selesai.")
                page.mouse.click(0, 0)

                try:
                    page.evaluate("window.onbeforeunload = null;")
                except Exception:
                    pass

                time.sleep(1)
                print("Menunggu observer submit & menutup browser...")

                batas_waktu_detik = 75
                interval_polling = 0.2
                waktu_mulai = time.time()
                while time.time() - waktu_mulai < batas_waktu_detik:

                    if event_selesai_manual is not None and event_selesai_manual.is_set():
                        ditutup_manual.set()
                        print("-> Observer klik 'Selesai' di aplikasi.")
                        break
                    if ditutup_manual.is_set():
                        print("-> Browser ditutup manual oleh observer.")
                        break

                    try:
                        if not browser.is_connected():
                            ditutup_manual.set()
                            print("-> Browser terdeteksi sudah tertutup (is_connected=False).")
                            break
                    except Exception:
                        ditutup_manual.set()
                        print("-> Browser terdeteksi sudah tertutup (exception saat cek koneksi).")
                        break

                    try:
                        if len(context.pages) == 0:
                            ditutup_manual.set()
                            print("-> Tab/halaman observer sudah tertutup (context.pages == 0).")
                            break
                    except Exception:
                        pass
                    time.sleep(interval_polling)

                _lapor_sukses()

            except Exception as e:
                print(f"Terjadi error: {e}")
                _lapor_gagal(str(e))

            finally:
                if browser and not ditutup_manual.is_set():
                    try:
                        browser.close()
                    except Exception:
                        pass


    threading.Thread(target=_worker_playwright, daemon=True).start()

    status, pesan = hasil_queue.get()
    if status == "gagal":
        raise Exception(pesan)


if __name__ == "__main__":
    contoh_data_cuaca = {
        "full_date": "2026-07-09",
        "hour": "00",
        "minute": "00",

        "is_cor": False,
        "is_nil": False,
        "is_auto": False,

        "direction": "090",
        "speed": "05",
        "gust": "",
        "dir_min": "",
        "dir_max": "",
        "is_vrb": False,

        "visibility": "8000",

        "temp": "27",
        "dew_point": "24",
        "pressure": "1010",

        "weather_intensity": None,
        "weather_descriptor": None,
        "weather_precipitation": None,
        "weather_obscuration": None,
        "weather_other": None,

        "recent_weather": None,

        "clouds": [
            {"amount": "FEW", "height": "010", "type": ""},
            {"amount": "SCT", "height": "025", "type": "CB"},
        ],
    }

    run_test(contoh_data_cuaca, nama_observer="Contoh Observer")
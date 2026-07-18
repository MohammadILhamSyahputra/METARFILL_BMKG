# fill_form.py
import os
import time
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
    Sesuaikan teks tombol ('OK', 'Simpan', 'Submit', 'Tutup') jika ternyata beda
    di form aslinya.
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
    print("-> Modal cuaca ditutup lewat tombol Escape (tombol submit tidak ditemukan, cek selector jika data tidak tersimpan).")


def run_test(data_cuaca, nama_observer):
    # if not os.path.exists("auth_state.json"):
    #     print("Error: File 'auth_state.json' tidak ditemukan!")
    #     return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="auth_state.json")
        page = context.new_page()
        page.set_default_timeout(60000)

        try:

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
            time.sleep(3)

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
                print(f"List tersedia: {observer_option.all_text_contents()}")

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
            # 4. URUTAN 4: VERIFIKASI FIELD ICAO (AUTOMATIC READONLY)
            # =========================================================
            print("\n[4] Memeriksa nilai otomatis ICAO...")
            page.wait_for_selector("#input-icao")
            nilai_icao = page.locator("#input-icao").input_value()
            print(f"-> Kode ICAO otomatis terisi: '{nilai_icao}'")

            # =========================================================
            # 5. URUTAN 5: ISI TANGGAL (BYPASS DATEPICKER LABEL)
            # =========================================================
            print(f"\n[5] Mengisi Tanggal: {data_cuaca['full_date']}...")

            page.click("#datepicker")
            page.keyboard.press("Control+KeyA")
            page.keyboard.press("Backspace")
            page.keyboard.type(data_cuaca['full_date'])  # Format: 2026-07-09
            page.keyboard.press("Enter")
            time.sleep(2)

            # =========================================================
            # 6 & 7. URUTAN 6 & 7: ISI JAM & MENIT
            # =========================================================
            print(f"\n[6 & 7] Mengisi Jam: {data_cuaca['hour']}, Menit: {data_cuaca['minute']}...")

            page.wait_for_selector("#input-jam")
            page.select_option("#input-jam", value=data_cuaca['hour'])

            page.wait_for_selector("#input-menit")
            page.select_option("#input-menit", value=data_cuaca['minute'])
            print(f"-> Waktu berhasil diset ke {data_cuaca['hour']}:{data_cuaca['minute']}")

            time.sleep(1)

            # =========================================================
            # [*] KELOMPOK DROPDOWN: TREND
            # =========================================================
            print("\n[*] Mengisi Trend...")
            target_trend = "NOSIG"
            print("-> Mengisi Trend via JavaScript bypass...")
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

            time.sleep(1)

            print("Menunggu web selesai mengambil data cuaca...")
            page.wait_for_selector(".vs__spinner", state="hidden")
            time.sleep(3)

            # =========================================================
            # 8. URUTAN 8: SINKRONISASI DATA ANGIN, VISIBILITY, SUHU, TEKANAN
            #    (VRB tidak lagi otomatis diklik di sini -- lihat langkah 9)
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
                    if (value === undefined || value === null) continue;
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
            # 9. URUTAN 9: CHECKBOX VRB (OTOMATIS JIKA KECEPATAN ANGIN > 2 KNOT)
            # =========================================================
            print("\n[9] Mengatur kondisi VRB...")
            kecepatan_angin = float(data_cuaca.get('speed', 0) or 0)
            vrb_harus_dicentang = kecepatan_angin > 2

            if vrb_harus_dicentang:
                # Cukup centang VRB saja, JANGAN kosongkan arah angin
                page.evaluate("""() => {
                    const cb = document.getElementById('checkbox-vrb');
                    if (cb) {
                        cb.checked = true;
                        cb.dispatchEvent(new Event('change', {bubbles: true}));
                        cb.dispatchEvent(new Event('input', {bubbles: true}));
                    }
                }""")
                print("-> VRB aktif, arah angin dipertahankan.")
            # print("\n[9] Memeriksa kondisi VRB...")
            # try:
            #     kecepatan_angin = float(data_cuaca.get('speed', 0) or 0)
            # except (TypeError, ValueError):
            #     kecepatan_angin = 0

            # vrb_harus_dicentang = kecepatan_angin > 2

            # PENTING: Sebelumnya di sini mencoba KLIK checkbox/label lewat UI
            # (page.locator(...).click()), tapi itu sering timeout 60 detik
            # dengan error "element is not visible" / "not stable". Ini
            # karena form BMKGSatu tampaknya MENYEMBUNYIKAN toggle VRB begitu
            # field arah angin (winds-direction) sudah diisi angka spesifik
            # di langkah 8 -- VRB dan arah angin numerik memang saling
            # eksklusif secara meteorologis. Karena elemen itu disembunyikan
            # (bukan sekadar di luar viewport), Playwright tidak akan pernah
            # menganggapnya "visible" sehingga klik lewat UI selalu gagal.
            #
            # Solusinya: set status checkbox langsung lewat JavaScript (mirip
            # cara Trend dipaksa di atas), tidak perlu elemen itu terlihat.
            # hasil_vrb = page.evaluate("""(shouldCheck) => {
            #     const cb = document.getElementById('checkbox-vrb');
            #     if (!cb) return { found: false };
            #     const before = cb.checked;
            #     if (cb.checked !== shouldCheck) {
            #         cb.checked = shouldCheck;
            #         cb.dispatchEvent(new Event('change', { bubbles: true }));
            #         cb.dispatchEvent(new Event('input', { bubbles: true }));
            #         cb.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            #     }
            #     return { found: true, before: before, after: cb.checked };
            # }""", vrb_harus_dicentang)

            # if not hasil_vrb.get("found"):
            #     print("-> WARNING: Checkbox VRB (#checkbox-vrb) tidak ditemukan di halaman, dilewati.")
            # else:
            #     print(f"-> Kecepatan angin {kecepatan_angin} knot -> target VRB={vrb_harus_dicentang}. "
            #           f"Status sebelum={hasil_vrb['before']}, sesudah={hasil_vrb['after']}.")

            # time.sleep(1)

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
                tombol_cuaca = page.locator("button.button-weather")
                tombol_cuaca.click()
                print("-> Modal Cuaca Saat Pengamatan dibuka.")

                # Modal BootstrapVue biasanya butuh sedikit waktu untuk animasi masuk
                page.wait_for_selector("div[id*='__BVID__'][id*='modal_body']", state="visible")
                modal = page.locator("div[id*='__BVID__'][id*='modal_body']")

                isi_radio_group(modal, "radio-intensity", data_cuaca.get("weather_intensity"))
                isi_radio_group(modal, "radio-descriptor", data_cuaca.get("weather_descriptor"))
                isi_radio_group(modal, "radio-precipitation", data_cuaca.get("weather_precipitation"))
                isi_radio_group(modal, "radio-obscuration", data_cuaca.get("weather_obscuration"))
                isi_radio_group(modal, "radio-other", data_cuaca.get("weather_other"))

                tutup_modal_cuaca(page)
                time.sleep(1)
            else:
                print("-> Tidak ada data Cuaca Saat Pengamatan, blok ini dilewati.")

            # =========================================================
            # 11. URUTAN 11: BLOK CUACA YANG LALU
            # =========================================================
            recent_weather = data_cuaca.get("recent_weather")
            if recent_weather is not None:
                print(f"\n[11] Mengisi Cuaca yang Lalu: '{recent_weather}'...")
                page.wait_for_selector("#recent-w-1")
                page.select_option("#recent-w-1", value=recent_weather)
                print("-> Cuaca yang Lalu berhasil diisi.")
            else:
                print("\n[11] Tidak ada data Cuaca yang Lalu, blok ini dilewati.")

            time.sleep(1)

            # =========================================================
            # 12. URUTAN 12: BLOK AWAN (MAKSIMAL 3 RECORD)
            # =========================================================
            daftar_awan = data_cuaca.get("clouds", [])[:3]  # hard limit 3 record
            print(f"\n[12] Mengisi Blok Awan ({len(daftar_awan)} record)...")

            for idx, awan in enumerate(daftar_awan, start=1):
                print(f"   -> Record awan #{idx}: {awan}")

                page.wait_for_selector("#clouds-jumlah")
                if awan.get("amount"):
                    page.select_option("#clouds-jumlah", value=awan["amount"])

                page.wait_for_selector("#cloud_height")
                if awan.get("height"):
                    # Kode tinggi awan METAR selalu 3 digit (mis. "020").
                    # zfill(3) untuk jaga-jaga kalau leading zero-nya hilang.
                    height_feet = int(awan["height"])
                    tinggi_awan = str(height_feet)
                    page.fill("#cloud_height", tinggi_awan)
                    page.evaluate("document.getElementById('cloud_height').dispatchEvent(new Event('input', {bubbles: true}));")
                    page.evaluate("document.getElementById('cloud_height').dispatchEvent(new Event('blur'));")

                page.wait_for_selector("#select-type")
                if awan.get("type"):
                    page.select_option("#select-type", value=awan["type"])
                else:
                    # Kosongkan pilihan Tipe Awan (opsi value="") jika tidak ada CB/TCU
                    page.select_option("#select-type", index=1) 
                    #page.evaluate("document.getElementById('select-type').dispatchEvent(new Event('change', {bubbles: true}));")

                # page.evaluate("document.getElementById('cloud_height').focus();")
                # page.evaluate("document.getElementById('cloud_height').blur();")
                page.evaluate("""() => {
                    const el = document.getElementById('select-type');
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    el.dispatchEvent(new Event('blur', {bubbles: true}));
                }""")
                
                # Tunggu sejenak agar JS form memproses
                time.sleep(1)

                # Klik tombol tambah record (ikon "+")
                tombol_tambah = page.locator("button.btn-success:has(svg.feather-plus)").first
                if tombol_tambah.count() == 0:
                    print(f"   -> WARNING: Tombol tambah awan tidak ditemukan untuk record #{idx}.")
                    continue

                # PENTING: sebelumnya langsung .click() tanpa mengecek status
                # disabled-nya tombol. Kalau form menganggap salah satu isian
                # (biasanya 'Tinggi Awan') tidak valid, tombolnya tetap
                # disabled dan Playwright menunggu sampai timeout 60 detik
                # baru melempar error, menghentikan seluruh proses kirim.
                # Sekarang kita tunggu maksimal 8 detik saja untuk tombolnya
                # menjadi enabled; kalau tetap disabled, kasih pesan
                # diagnostik yang jelas dan lanjut ke record berikutnya
                # (bukan menghentikan seluruh pengiriman).
                try:
                    # page.wait_for_function(
                    #     "(btn) => btn && !btn.disabled",
                    #     arg=tombol_tambah.element_handle(),
                    #     timeout=8000,
                    # )
                    # tombol_tambah.click()
                    # print(f"   -> Record awan #{idx} ditambahkan.")
                    tombol_tambah.click(force=True, timeout=5000)
                    print(f"   -> Record awan #{idx} berhasil diklik.")
                except Exception:
                    # print(f"   -> WARNING: Tombol tambah awan tetap disabled untuk record #{idx} "
                    #       f"(amount='{awan.get('amount')}', height='{tinggi_awan if awan.get('height') else ''}', "
                    #       f"type='{awan.get('type', '')}'). Kemungkinan salah satu nilai di atas tidak "
                    #       f"valid menurut form (mis. format Tinggi Awan). Record ini DILEWATI, cek manual di browser.")
                    print(f"   -> WARNING: Gagal klik tombol tambah, mencoba JS click(). Error: {e}")
                    # Backup plan: klik langsung via JavaScript DOM
                    page.evaluate("document.querySelector('button.btn-success:has(svg.feather-plus)').click()")
                    print(f"   -> Record awan #{idx} ditambahkan via JS.")

                time.sleep(1)

            if not daftar_awan:
                print("-> Tidak ada data Awan, blok ini dilewati.")

            print("-> Injeksi data selesai.")
            page.mouse.click(0, 0)

            time.sleep(5)
            print("Pengiriman selesai.")

            print("Observer memiliki waktu 60 detik untuk memeriksa data.")
            time.sleep(60)

        except Exception as e:
            print(f"Terjadi error: {e}")
            raise e

        finally:
            if browser:
                browser.close()


if __name__ == "__main__":
    # Contoh struktur data_cuaca yang dipakai oleh run_test().
    # Sesuaikan value radio/select dengan atribut 'value' pada HTML di field_bmkg_soft.txt
    contoh_data_cuaca = {
        "full_date": "2026-07-09",
        "hour": "00",
        "minute": "00",

        # Angin
        "direction": "090",
        "speed": "05",       # > 2 knot -> VRB otomatis tercentang
        "gust": "",          # input#wind_gust, boleh dikosongkan
        "dir_min": "",
        "dir_max": "",

        # Visibility
        "visibility": "8000",

        # Suhu / Titik embun / Tekanan
        "temp": "27",
        "dew_point": "24",
        "pressure": "1010",

        # Cuaca Saat Pengamatan (isi None untuk melewati grup tsb sepenuhnya)
        "weather_intensity": None,
        "weather_descriptor": None,
        "weather_precipitation": None,
        "weather_obscuration": None,
        "weather_other": None,

        # Cuaca yang Lalu (isi None untuk melewati)
        "recent_weather": None,

        # Awan, maksimal 3 record
        "clouds": [
            {"amount": "FEW", "height": "010", "type": ""},
            {"amount": "SCT", "height": "025", "type": "CB"},
        ],
    }

    run_test(contoh_data_cuaca, nama_observer="Contoh Observer")
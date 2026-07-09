# fill_form.py
import os
import time
from playwright.sync_api import sync_playwright

def run_test(data_cuaca):
    if not os.path.exists("auth_state.json"):
        print("Error: File 'auth_state.json' tidak ditemukan!")
        return

    p = sync_playwright().start()
    browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
    context = browser.new_context(storage_state="auth_state.json")
    page = context.new_page()
    
    page.set_default_timeout(60000)
    
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
    observer_target = "Alfi"  # <-- Nama observer otomatis Anda
    observer_container = page.locator("div.form-group:has(label:has-text('Nama Observer'))")
    observer_search = observer_container.locator(".vs__search")
    
    observer_search.click()
    observer_search.fill(observer_target)
    
    observer_option = observer_container.locator(f"ul[role='listbox'] li:has-text('{observer_target}')")
    observer_option.wait_for(state="visible")
    observer_option.click()
    print(f"-> Nama Observer '{observer_target}' Berhasil dipilih!")
    
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
    
    # Fokuskan ke input
    page.click("#datepicker")
    
    # Hapus isi lama jika ada (Ctrl+A lalu Backspace)
    page.keyboard.press("Control+KeyA")
    page.keyboard.press("Backspace")
    
    # Ketik tanggal secara manual (seolah user mengetik)
    page.keyboard.type(data_cuaca['full_date']) # Format: 2026-07-09
    
    # Tekan Enter untuk mengunci tanggal
    page.keyboard.press("Enter")
    
    # Tunggu agar web sempat memproses 'Generate Sandi'
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
    # [*] KELOMPOK DROPDOWN: AWAN & TREND (SINKRONISASI DROPDOWN)
    # =========================================================
    print("\n[*] Mengisi Dropdown Awan & Trend...")
    
    # A. Isi Jumlah Awan
    # page.wait_for_selector("#clouds-jumlah")
    # page.select_option("#clouds-jumlah", value="SCT")
    
    # # B. Isi Tipe Awan
    # page.wait_for_selector("#select-type")
    # page.select_option("#select-type", value="CB")
    
    # C. Isi Trend (Bypass Hidden Element dengan JavaScript)
    print("-> Mengisi Trend via JavaScript bypass...")
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
    
    time.sleep(1)

    print("Menunggu web selesai mengambil data cuaca...")
    page.wait_for_selector(".vs__spinner", state="hidden") # Tunggu spinner loading hilang
    time.sleep(3)

    # =========================================================
    # 8. URUTAN 8: SINKRONISASI TOTAL BLOK DATA CUACA VIA JS INJECTION
    # =========================================================
    print(f"\n[8] Menginjeksi data: {data_cuaca}")
    page.evaluate(f"""(data) => {{
        const triggerEvent = (el) => {{
            if (el) {{
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }};

        // 1. INJEKSI DATA CUACA
        const mapping = {{
            'winds-direction': data.direction,
            'wind_speed': data.speed,
            'winds-wd-dn': data.dir_min,
            'winds-wd-dx': data.dir_max,
            'input-prevailing': data.visibility,
            'clouds-jumlah': data.cloud_amount,
            'cloud_height': data.cloud_height,
            'v-air-temp': data.temp,
            'v-dew-point': data.dew_point,
            'v-presure': data.pressure
        }};

        for (const [id, value] of Object.entries(mapping)) {{
            const el = document.getElementById(id);
            if (el) {{
                el.value = value;
                triggerEvent(el);
            }}
        }}

        // 2. INJEKSI TREND (Lakukan tepat setelah data cuaca)
        const trendSelect = document.querySelector('select[data-v-1010a25b]#input-type');
        if (trendSelect) {{
            trendSelect.value = 'NOSIG'; 
            triggerEvent(trendSelect);
        }}

        // 3. TERAKHIR: Injeksi VRB agar tidak tertimpa/terreset
        const vrb = document.getElementById('checkbox-vrb');
        if (vrb && !vrb.checked) {{
            vrb.click();
            triggerEvent(vrb);
        }}
    }}""", data_cuaca)
        
    print("-> Injeksi data selesai.")
    page.mouse.click(0, 0)
        
    # Tambahkan jeda waktu agar Anda bisa melihat hasil injeksi
    print("Menunggu 20 detik sebelum menutup browser...")
    time.sleep(20) 
        
    # Atau gunakan ini agar browser tidak tertutup sampai Anda menekan Enter
    input("Tekan ENTER di terminal untuk menutup browser...")
    browser.close()

if __name__ == "__main__":
    run_test()
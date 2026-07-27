import os
from playwright.sync_api import sync_playwright

def save_auth():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    auth_path = os.path.join(current_dir, "auth_state.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Buka halaman login BMKG
        print("Membuka halaman... Silakan login secara manual di browser yang terbuka.")
        page.goto("https://bmkgsatu.bmkg.go.id/")
        page.pause() 

        # Menyimpan status login (cookies, local storage, dll) ke file JSON
        # -> auth_state.json ini yang jadi SATU-SATUNYA sumber kredensial,
        #    dipakai oleh monitoring_page.py lewat auth_utils.build_auth_config()
        context.storage_state(path=auth_path)
        print(f"Status login berhasil disimpan ke '{auth_path}'!")
        
        browser.close()

if __name__ == "__main__":
    save_auth()
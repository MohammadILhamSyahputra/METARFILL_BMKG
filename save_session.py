import os
from playwright.sync_api import sync_playwright

def save_auth():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Buka halaman login BMKG
        print("Membuka halaman... Silakan login secara manual di browser yang terbuka.")
        page.goto("https://bmkgsatu.bmkg.go.id/")
        page.pause() 

        # Menyimpan status login (cookies, local storage, dll) ke file JSON
        context.storage_state(path="auth_state.json")
        print("Status login berhasil disimpan ke 'auth_state.json'!")
        
        browser.close()

if __name__ == "__main__":
    save_auth()
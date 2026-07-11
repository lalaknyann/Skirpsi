import os
import sys
import time
import requests
from dotenv import load_dotenv

# Load env variables
load_dotenv()

USERNAME = os.environ.get("PYTHONANYWHERE_USERNAME", "gavrilana")
TOKEN = os.environ.get("PYTHONANYWHERE_API_TOKEN", "395ec823467e1e6b24eb8d5123c8dd6f65954c84")
DOMAIN = os.environ.get("PYTHONANYWHERE_DOMAIN", f"{USERNAME}.pythonanywhere.com")

headers = {'Authorization': f'Token {TOKEN}'}
base_url = f'https://www.pythonanywhere.com/api/v0/user/{USERNAME}'

def deploy():
    print("==============================================")
    print("       DEPLOYING TO PYTHONANYWHERE            ")
    print("==============================================")
    
    # 1. Get or create bash console
    print("1. Menghubungi PythonAnywhere Console API...")
    consoles_url = f'{base_url}/consoles/'
    
    try:
        res = requests.get(consoles_url, headers=headers)
        if res.status_code != 200:
            print(f"[FAILED] Gagal mengambil list console: {res.status_code} - {res.text}")
            return
            
        consoles = res.json()
        bash_console = None
        for c in consoles:
            if c.get('executable') == 'bash':
                bash_console = c
                break
                
        if bash_console:
            console_id = bash_console['id']
            print(f"[OK] Menggunakan console bash yang aktif (ID: {console_id})")
        else:
            print("[INFO] Membuat console bash baru...")
            res = requests.post(consoles_url, headers=headers, json={"executable": "bash"})
            if res.status_code != 201:
                print(f"[FAILED] Gagal membuat console baru: {res.status_code} - {res.text}")
                return
            bash_console = res.json()
            console_id = bash_console['id']
            print(f"[OK] Console bash baru berhasil dibuat (ID: {console_id})")
            
        # 2. Run git pull command
        print("\n2. Mengirimkan perintah 'git pull' ke PythonAnywhere...")
        input_url = f'{consoles_url}{console_id}/send_input/'
        
        # Pull latest code from GitHub
        command = "cd ~/Skirpsi && git pull\n"
        res = requests.post(input_url, headers=headers, json={"input": command})
        if res.status_code == 412:
            print("\n[TIPS] Error 412: Console baru belum diaktifkan oleh sistem PythonAnywhere.")
            print("Silakan ikuti langkah mudah ini:")
            print("1. Buka browser dan login ke https://www.pythonanywhere.com/")
            print("2. Masuk ke tab 'Consoles' dan buka salah satu console 'Bash'.")
            print("3. Setelah console terbuka di browser, jalankan kembali script deploy.py ini.")
            return
        elif res.status_code != 200:
            print(f"[FAILED] Gagal mengirim perintah pull: {res.status_code} - {res.text}")
            return
        
        print("[OK] Perintah pull terkirim. Menunggu 5 detik agar git pull selesai...")
        time.sleep(5)
        
        # 3. Reload Webapp
        print(f"\n3. Melakukan reload webapp di {DOMAIN}...")
        reload_url = f'{base_url}/webapps/{DOMAIN}/reload/'
        res = requests.post(reload_url, headers=headers)
        if res.status_code == 200:
            print("\n==============================================")
            print("  [SUCCESS] Webapp berhasil di-deploy & reload! ")
            print(f"  Link: http://{DOMAIN}")
            print("==============================================")
        else:
            print(f"[FAILED] Gagal reload webapp: {res.status_code} - {res.text}")
            print("TIPS: Pastikan domain name di PythonAnywhere sudah dibuat.")
            
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan: {e}")

if __name__ == '__main__':
    deploy()

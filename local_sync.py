import os
import requests

USERNAME = "gavrilana"
TOKEN = "395ec823467e1e6b24eb8d5123c8dd6f65954c84"
headers = {'Authorization': f'Token {TOKEN}'}

# List of files/folders to exclude
EXCLUDE_DIRS = {'.git', '.gemini', '__pycache__', '.agents', '.virtualenvs', '.cache', 'scratch', '.git_backup'}
EXCLUDE_FILES = {'.env', 'local_sync.py', 'scratch_generate_lag_plot.py'}

def sync_files():
    print("==============================================")
    print("      SYNCING FILES TO PYTHONANYWHERE         ")
    print("==============================================")
    
    local_root = os.path.dirname(os.path.abspath(__file__))
    
    for root, dirs, files in os.walk(local_root):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file in EXCLUDE_FILES:
                continue
                
            # Exclude large raw figures in output/figures except results.json
            rel_path = os.path.relpath(os.path.join(root, file), local_root)
            if rel_path.startswith("output\\figures") or rel_path.startswith("output/figures"):
                if file != "results.json" and file != "gambar_4_5_lag_nan.png" and file != "lag_nan_visualization.png":
                    continue
            if rel_path.startswith("figures\\") or rel_path.startswith("figures/"):
                continue
                
            local_file_path = os.path.join(root, file)
            # Use forward slashes for PythonAnywhere paths
            remote_rel_path = rel_path.replace("\\", "/")
            remote_file_path = f"/home/{USERNAME}/Skirpsi/{remote_rel_path}"
            
            print(f"Uploading: {remote_rel_path} ...", end="", flush=True)
            
            # Read file content
            with open(local_file_path, "rb") as f:
                content = f.read()
                
            # Send file to PythonAnywhere API
            url = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}/files/path{remote_file_path}"
            res = requests.post(url, headers=headers, files={'content': content})
            
            if res.status_code in [200, 201]:
                print(" [OK]")
            else:
                print(f" [FAILED] (Status: {res.status_code} - {res.text})")

    # Reload Webapp
    print("\nReloading webapp to apply changes...")
    reload_url = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}/webapps/{USERNAME}.pythonanywhere.com/reload/"
    res = requests.post(reload_url, headers=headers)
    if res.status_code == 200:
        print("[SUCCESS] Webapp reloaded successfully!")
    else:
        print(f"[FAILED] Gagal reload: {res.status_code} - {res.text}")

if __name__ == "__main__":
    sync_files()

import subprocess
import sys

def delete_files():
    with open('files_to_delete.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"Found {len(lines)} files to delete.")
    
    count = 0
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 8:
            continue
            
        # Extract filename (from index 7 onwards)
        # Verify date matches just in case
        if parts[5] != '2026-02-12':
            print(f"Skipping (wrong date): {line}")
            continue
            
        filename = " ".join(parts[7:])
        
        # Escape quotes for shell
        safe_filename = filename.replace('"', '\\"')
        path = f'/storage/emulated/0/snaptube/download/Snaptube Audio/{safe_filename}'
        
        cmd = ['adb', 'shell', 'rm', f'"{path}"']
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            # print(f"Deleted: {filename}")
            count += 1
            if count % 10 == 0:
                print(f"Deleted {count} files...", end='\r')
        except subprocess.CalledProcessError as e:
            print(f"Error deleting {filename}: {e}")

    print(f"\nFinished. Deleted {count} files.")

if __name__ == '__main__':
    delete_files()

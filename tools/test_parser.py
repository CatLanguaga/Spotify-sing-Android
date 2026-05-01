import re, subprocess
from datetime import datetime
from pathlib import Path

PHONE_DIR = '/storage/emulated/0/snaptube/download/Snaptube Audio'
SUPPORTED_EXT = {'.mp3', '.m4a', '.flac'}
DATE_RE = re.compile(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+(.*)')

r = subprocess.run(['adb', 'shell', f'ls -la "{PHONE_DIR}"'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
lines = r.stdout.strip().split('\n') + r.stderr.strip().split('\n')

dated = []
for line in lines:
    m = DATE_RE.search(line)
    if not m: continue
    date_part, time_part, fname = m.group(1), m.group(2), m.group(3).strip()
    if Path(fname).suffix.lower() not in SUPPORTED_EXT: continue
    try:
        dt = datetime.strptime(f'{date_part} {time_part}', '%Y-%m-%d %H:%M')
    except: dt = datetime.min
    dated.append((dt, fname))

dated.sort(key=lambda x: x[0])
print(f'Total parseados: {len(dated)}')
for dt, fn in dated[:5]:
    print(f'  {dt.strftime("%Y-%m-%d %H:%M")} -> {fn}')

# Test pull del primero
if dated:
    fn = dated[0][1]
    dst = f'C:/Users/ardie/.openclaw/workspace/temp_meta/test_fix.mp3'
    cmd = f'adb pull "{PHONE_DIR}/{fn}" "{dst}"'
    r2 = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    exists = Path(dst).exists() and Path(dst).stat().st_size > 0
    print(f'\nTest pull "{fn}": {"OK" if exists else "FAIL"}')

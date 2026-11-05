"""Scan for stub vs real implementations."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

stubs = []
real = []
base = r'D:\intelligent-classroom-monitoring'

for root, dirs, files in os.walk(base):
    dirs[:] = [d for d in dirs if d not in ('node_modules','__pycache__','.git','dist','archive','.system_generated')]
    for f in files:
        if not f.endswith('.py'): continue
        path = os.path.join(root, f)
        rel = os.path.relpath(path, base)
        try:
            content = open(path, encoding='utf-8').read()
        except: continue
        lines = content.strip().split('\n')
        nlines = len(lines)
        has_na = 'N/A' in content or 'Not yet' in content
        has_pass = content.count('\n    pass') + content.count('\n        pass')
        
        if nlines < 15 and '__init__' not in f:
            stubs.append(f'{rel} [{nlines}L] MINIMAL')
        elif has_na and nlines < 50:
            stubs.append(f'{rel} [{nlines}L] STUB')
        elif has_pass > 3:
            stubs.append(f'{rel} [{nlines}L] MANY_PASS')
        else:
            real.append(f'{rel} [{nlines}L]')

print('=== STUB/MINIMAL FILES ===')
for s in sorted(stubs): print(f'  {s}')
print(f'\nTotal stubs: {len(stubs)}')
print(f'\n=== REAL IMPLEMENTATIONS ===')
for r in sorted(real): print(f'  {r}')
print(f'\nTotal real: {len(real)}')

import sys
from pathlib import Path

def main():
    diag = Path("diagnose.py")
    if not diag.exists():
        print("diagnose.py не найден, визуальная диагностика пропущена")
        return 0
    import subprocess
    p = subprocess.run([sys.executable, "diagnose.py"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(p.stdout)
    if p.returncode != 0:
        print("Визуальная диагностика показала проблемы")
        return 2
    print("Визуальная диагностика: всё OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())

"""Script para empacotar o Analisador Viral em um .exe usando PyInstaller.

Uso:
    python build.py
"""
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent
DIST = PROJECT_ROOT / "dist"
BUILD = PROJECT_ROOT / "build"
SPEC = PROJECT_ROOT / "AnalisadorViral.spec"


def _clean():
    for path in (DIST, BUILD):
        if path.exists():
            shutil.rmtree(path)
    if SPEC.exists():
        SPEC.unlink()


def main():
    print("Limpando builds anteriores...")
    _clean()

    print("Rodando PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "AnalisadorViral",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--collect-all", "customtkinter",
        "app.py",
    ]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("\nERRO: PyInstaller falhou.")
        sys.exit(result.returncode)

    exe = DIST / "AnalisadorViral.exe"
    if exe.exists():
        print(f"\nBuild concluído! Executável em: {exe}")
        print(f"Tamanho: {exe.stat().st_size / (1024 * 1024):.1f} MB")
    else:
        print("\nErro: executável não foi gerado.")
        sys.exit(1)


if __name__ == "__main__":
    main()

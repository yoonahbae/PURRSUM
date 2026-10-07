#!/usr/bin/env bash
# Rebuild "Install PurrSum Noir.exe" from source on Linux.
# Needs: python3, pip, curl, makensis (apt install nsis). Run from the build/ folder.
set -euo pipefail
cd "$(dirname "$0")"

PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/20250115/cpython-3.12.8%2B20250115-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"

rm -rf stage wheels && mkdir -p stage wheels

# 1. Portable Windows Python 3.12
curl -sSL -o py.tgz "$PY_URL"
tar xzf py.tgz -C stage && rm py.tgz

# 2. Windows wheels bundled in the installer (the big OCR engine is downloaded at
#    install time instead, see app/purrsum/engine_files.json + setup_engine.py)
pip download -q --dest wheels --only-binary=:all: --platform win_amd64 \
  --python-version 3.12 --implementation cp --no-deps \
  PySide6-Essentials==6.11.2 shiboken6==6.11.2 shapely==2.1.2 pyclipper==1.4.0 \
  pyyaml==6.0.3 six==1.17.0 flatbuffers packaging protobuf
SP=stage/python/Lib/site-packages
for w in wheels/*.whl; do python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$w" "$SP"; done

# 3. Trim what the app doesn't use
python3 prune.py stage/python
rm -rf "$SP/pip" "$SP"/pip-*
cp stage/python/pythonw.exe "stage/python/PurrSum Noir.exe"   # nicer name in Task Manager

# 4. App + icon
mkdir -p stage/app && cp -r ../app/purrsum ../app/purrsum.pyw stage/app/
find stage/app -name __pycache__ -exec rm -rf {} +
cp purrsum.ico stage/purrsum.ico

# 5. One-file installer (64-bit, per-user, no admin)
makensis -V2 installer.nsi
ls -la "Install PurrSum Noir.exe"

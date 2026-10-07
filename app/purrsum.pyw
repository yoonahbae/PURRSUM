import os, sys

# pythonw has no console: send any stray output to a small log instead of crashing
if sys.stdout is None or sys.stderr is None:
    try:
        d = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "PurrSum Noir")
        os.makedirs(d, exist_ok=True)
        log = open(os.path.join(d, "log.txt"), "a", encoding="utf-8", buffering=1)
    except Exception:
        log = open(os.devnull, "w")
    sys.stdout = sys.stdout or log
    sys.stderr = sys.stderr or log

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from purrsum.ui import main
sys.exit(main())

import os
import shutil
import subprocess
from pathlib import Path


def open_with_default_application(filepath):
    filepath = Path(filepath).expanduser().resolve()
    if os.name == "nt":
        os.startfile(str(filepath))  # type: ignore[attr-defined]
        return

    opener = shutil.which("xdg-open") or shutil.which("open")
    if opener is None:
        raise RuntimeError("No system opener found.")
    subprocess.Popen([opener, str(filepath)])

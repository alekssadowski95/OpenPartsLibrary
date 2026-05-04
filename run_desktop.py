import os
import sys
from pathlib import Path


def configure_desktop_data_dir():
    if "OPENPARTSLIBRARY_DATA_DIR" in os.environ:
        return

    if getattr(sys, "frozen", False):
        os.environ["OPENPARTSLIBRARY_DATA_DIR"] = str(Path(sys.executable).resolve().parent / "data")


configure_desktop_data_dir()

from openpartslibrary import app

import webview


if __name__ == '__main__':

    window = webview.create_window('OpenPartsLibrary', app)

    try:
        import pyi_splash # type: ignore

        # Close the splash screen. It does not matter when the call
        # to this function is made, the splash screen remains open until
        # this function is called or the Python program is terminated.
        pyi_splash.close()
    except:
        pass

    webview.start()

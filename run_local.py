from openpartslibrary_flask import app

import webview


if __name__ == '__main__':

    window = webview.create_window('OpenPartsLibrary', app)

    try:
        import pyi_splash

        # Close the splash screen. It does not matter when the call
        # to this function is made, the splash screen remains open until
        # this function is called or the Python program is terminated.
        pyi_splash.close()
    except:
        pass

    webview.start()
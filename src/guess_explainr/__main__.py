import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def main() -> None:
    threading.Timer(2, webbrowser.open, args=[URL]).start()
    uvicorn.run("guess_explainr.app:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()

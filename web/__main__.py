"""Start the Socks web app:  py -m web  [--port 5050] [--no-browser]"""

import argparse
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Socks web app on this computer.")
    parser.add_argument("--port", type=int, default=5050, help="port to use (default 5050)")
    parser.add_argument("--no-browser", action="store_true", help="don't open the browser")
    args = parser.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((HOST, args.port))
        except OSError:
            sys.exit(
                f"\n  Port {args.port} is already in use. Socks may already be running;\n"
                f"  try http://{HOST}:{args.port}/ or start it with:  py -m web --port {args.port + 1}\n"
            )

    # The data layer finds the database relative to the repo root.
    os.chdir(ROOT)
    from web.app import create_app

    app = create_app()
    url = f"http://{HOST}:{args.port}/"

    print()
    print("  SOCKS is running.")
    print(f"  Open {url} in your browser.")
    print("  Press Ctrl+C in this window to stop it.")
    print()

    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()

    app.run(host=HOST, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

"""Serve the sample workspace locally without dependencies or credentials."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[1] / "app" / "web"
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"QueryMind sample workspace: http://127.0.0.1:{args.port}", flush=True)
        print("Sample mode only. Use the FastAPI backend for live queries.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()

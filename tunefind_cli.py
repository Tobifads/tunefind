from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from app.service import TuneFindService


def main() -> None:
    parser = argparse.ArgumentParser(description="TuneFind MVP CLI")
    parser.add_argument("--data-dir", default="data", help="Data directory for uploads/index")
    sub = parser.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("upload")
    up.add_argument("--owner-id", required=True)
    up.add_argument("--file", required=True)

    se = sub.add_parser("search")
    se.add_argument("--owner-id", required=True)
    se.add_argument("--file", required=True, help="Hummed WAV/MP3 file")
    se.add_argument("--top-k", type=int, default=5)

    sub.add_parser("setup-keyfinder", help="Install ffmpeg + keyfinder-cli system dependencies")
    sub.add_parser("setup-deps", help="Install all default dependencies (pip + system)")

    args = parser.parse_args()
    service = TuneFindService(Path(args.data_dir))

    if args.cmd == "upload":
        path = Path(args.file)
        result = service.upload_beat(args.owner_id, path.name, path.read_bytes())
        print(result)
    elif args.cmd == "search":
        result = service.search_by_hum(args.owner_id, Path(args.file).read_bytes(), top_k=args.top_k)
        print(result)
    elif args.cmd == "setup-keyfinder":
        script = Path(__file__).resolve().parent / "scripts" / "setup_default_deps.py"
        if not script.exists():
            print("setup_default_deps.py not found.")
            sys.exit(1)
        result = subprocess.run([sys.executable, str(script), "--keyfinder-only"])
        sys.exit(result.returncode)
    elif args.cmd == "setup-deps":
        script = Path(__file__).resolve().parent / "scripts" / "setup_default_deps.py"
        if not script.exists():
            print("setup_default_deps.py not found.")
            sys.exit(1)
        result = subprocess.run([sys.executable, str(script)])
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()

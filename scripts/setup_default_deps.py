from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> None:
    printable = " ".join(cmd)
    print(f"+ {printable}")
    subprocess.run(cmd, check=True)


def install_python_requirements() -> None:
    req = ROOT_DIR / "requirements.txt"
    run([sys.executable, "-m", "pip", "install", "-r", str(req)])


def install_system_keyfinder() -> None:
    system = platform.system()
    if system == "Windows":
        script = ROOT_DIR / "scripts" / "install_keyfinder_cli.ps1"
        runner = shutil.which("powershell") or shutil.which("pwsh")
        if not runner:
            raise RuntimeError("PowerShell is required on Windows to run install_keyfinder_cli.ps1")
        run(
            [
                runner,
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
            ]
        )
        return

    script = ROOT_DIR / "scripts" / "install_keyfinder_cli.sh"
    run(["bash", str(script)])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install default TuneFind dependencies (Python + ffmpeg + keyfinder-cli)."
    )
    parser.add_argument(
        "--keyfinder-only",
        action="store_true",
        help="Only install system keyfinder/ffmpeg dependencies.",
    )
    args = parser.parse_args()

    if not args.keyfinder_only:
        install_python_requirements()
    install_system_keyfinder()
    print("Dependency setup finished.")


if __name__ == "__main__":
    main()

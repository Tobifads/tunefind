#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TOOLS_DIR="$ROOT_DIR/.tools"
SRC_DIR="$TOOLS_DIR/keyfinder-cli-src"
PREFIX_DIR="$TOOLS_DIR/keyfinder-cli"

install_macos_deps() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is required to install default dependencies on macOS."
    echo "Install Homebrew, then re-run this script."
    exit 1
  fi

  if ! command -v cmake >/dev/null 2>&1; then
    echo "Installing cmake via Homebrew..."
    brew install cmake
  fi
  if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Installing ffmpeg via Homebrew..."
    brew install ffmpeg
  fi
  if ! brew list libkeyfinder >/dev/null 2>&1; then
    echo "Installing libkeyfinder via Homebrew..."
    brew install libkeyfinder
  fi
}

install_linux_deps() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "Installing dependencies via apt..."
    sudo apt-get update
    sudo apt-get install -y ffmpeg libkeyfinder-dev cmake git pkg-config
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    echo "Installing dependencies via dnf..."
    sudo dnf install -y ffmpeg libkeyfinder-devel cmake git pkgconf-pkg-config
    return
  fi
  if command -v pacman >/dev/null 2>&1; then
    echo "Installing dependencies via pacman..."
    sudo pacman -S --noconfirm ffmpeg libkeyfinder cmake git pkgconf
    return
  fi
  echo "Unsupported Linux distribution."
  echo "Install ffmpeg + libkeyfinder + cmake + git manually, then re-run."
  exit 1
}

case "$(uname -s)" in
  Darwin)
    install_macos_deps
    ;;
  Linux)
    install_linux_deps
    ;;
  *)
    echo "This script supports macOS and Linux."
    echo "On Windows, run scripts/install_keyfinder_cli.ps1"
    exit 1
    ;;
esac

if ! command -v git >/dev/null 2>&1; then
  echo "git is required."
  exit 1
fi

if ! command -v cmake >/dev/null 2>&1; then
  echo "cmake is required."
  exit 1
fi

mkdir -p "$TOOLS_DIR"

if [ ! -d "$SRC_DIR" ]; then
  git clone https://github.com/evanpurkhiser/keyfinder-cli "$SRC_DIR"
else
  git -C "$SRC_DIR" pull --ff-only
fi

cmake -S "$SRC_DIR" -B "$SRC_DIR/build" -DCMAKE_INSTALL_PREFIX="$PREFIX_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$SRC_DIR/build" --config Release
cmake --install "$SRC_DIR/build" --config Release

BIN="$PREFIX_DIR/bin/keyfinder-cli"
if [ -f "$BIN" ]; then
  echo "keyfinder-cli installed at: $BIN"
else
  echo "keyfinder-cli build finished, but binary not found at $BIN"
  exit 1
fi

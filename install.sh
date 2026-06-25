#!/usr/bin/env sh
# Valzhar's MBII Manager — Setup (Linux)

set -e

PY="python3"
SCRIPTPATH="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "  Valzhar's MBII Manager"
echo "========================================"
echo ""

# ── Python ──
if ! command -v $PY >/dev/null 2>&1; then
    echo "ERROR: Python 3 not found."
    if command -v apt-get >/dev/null 2>&1; then
        echo "  sudo apt-get install python3"
    elif command -v dnf >/dev/null 2>&1; then
        echo "  sudo dnf install python3"
    elif command -v pacman >/dev/null 2>&1; then
        echo "  sudo pacman -S python"
    fi
    exit 1
fi
echo "  [OK] $($PY --version 2>&1)"

# ── Distro detection ──
if command -v apt-get >/dev/null 2>&1; then
    PKG="apt"
elif command -v dnf >/dev/null 2>&1; then
    PKG="dnf"
elif command -v pacman >/dev/null 2>&1; then
    PKG="pacman"
else
    PKG=""
fi

# ── 32-bit libs + mimalloc ──
case "$PKG" in
    apt)
        echo "  [....] Debian/Ubuntu — installing 32-bit libs..."
        sudo dpkg --add-architecture i386 2>/dev/null
        sudo apt-get update -qq
        sudo apt-get install -y libc6:i386 lib32z1 libstdc++6:i386 libcurl4t64:i386 2>/dev/null || \
        sudo apt-get install -y libc6:i386 lib32z1 libstdc++6:i386 libcurl4:i386
        sudo apt-get install -y libmimalloc-dev:i386 2>/dev/null || \
        sudo apt-get install -y libmimalloc2:i386 2>/dev/null || \
        echo "  [WARN] mimalloc i386 not found — install manually"
        echo "  [OK] 32-bit libs installed"
        ;;
    dnf)
        echo "  [....] Fedora/RHEL — installing 32-bit libs..."
        sudo dnf install -y glibc.i686 libstdc++.i686 libcurl.i686
        sudo dnf install -y mimalloc.i686 2>/dev/null || \
        echo "  [WARN] mimalloc.i686 not found — install manually"
        echo "  [OK] 32-bit libs installed"
        ;;
    pacman)
        echo "  [....] Arch — installing 32-bit libs..."
        sudo pacman -S --noconfirm lib32-glibc lib32-gcc-libs lib32-curl
        sudo pacman -S --noconfirm lib32-mimalloc 2>/dev/null || \
        echo "  [WARN] lib32-mimalloc not found — install manually"
        echo "  [OK] 32-bit libs installed"
        ;;
    *)
        echo "  [SKIP] Unknown distro — install 32-bit libs + mimalloc manually"
        ;;
esac

# ── Symlinks ──
OPENJK_TARGET="$HOME/openjk"
mkdir -p "$OPENJK_TARGET/MBII"
mkdir -p "$HOME/.local/share"
ln -sf "$OPENJK_TARGET" "$HOME/.local/share/openjk" 2>/dev/null || true
ln -sf "$OPENJK_TARGET" "$HOME/.ja" 2>/dev/null || true

# ── CLI shortcut ──
sudo ln -sf "$SCRIPTPATH/manager.py" "/usr/bin/mbii"
echo "  [OK] Shortcut: mbii"

# ── .NET SDK 6.0 ──
if [ ! -d "$HOME/.dotnet" ]; then
    echo "  [....] Installing .NET SDK 6.0..."
    cd "$SCRIPTPATH"
    wget -q https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh
    chmod +x dotnet-install.sh
    ./dotnet-install.sh --channel 6.0 2>/dev/null
    echo "  [OK] .NET SDK 6.0 installed"
fi

# ── MBII updater files ──
if [ -d "$SCRIPTPATH/updater" ]; then
    cp "$SCRIPTPATH/updater/"*.dll "$SCRIPTPATH/updater/"*.exe "$SCRIPTPATH/updater/"*.json "$OPENJK_TARGET/" 2>/dev/null || true
    echo "  [OK] Updater files copied to openjk/"
fi

echo ""
echo "========================================"
echo "  Setup complete"
echo "========================================"
echo ""
echo "  mbii <name> start|stop|restart|status"
echo "  mbii --update"

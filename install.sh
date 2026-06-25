#!/usr/bin/env sh
# Valzhar's MBII Server Manager — Setup (Linux)

set -e

PY="python3"
SCRIPTPATH="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "  Valzhar's MBII Server Manager"
echo "========================================"
echo ""

# ── Python ──
if ! command -v $PY >/dev/null 2>&1; then
    echo "ERROR: Python 3 not found.  apt install python3"
    exit 1
fi
echo "  [OK] $($PY --version 2>&1)"

# ── 32-bit libs ──
if command -v dpkg >/dev/null 2>&1; then
    for lib in libc6:i386 lib32z1 libstdc++6:i386 libcurl4t64:i386; do
        if ! dpkg -l "$lib" 2>/dev/null | grep -q "^ii"; then
            MISSING="$MISSING $lib"
        fi
    done
    if [ -n "$MISSING" ]; then
        sudo dpkg --add-architecture i386 2>/dev/null
        sudo apt-get update -qq
        sudo apt-get install -y $MISSING
        echo "  [OK] 32-bit libs installed"
    fi

    if ! dpkg -l libjemalloc2:i386 2>/dev/null | grep -q "^ii"; then
        sudo apt-get install -y libjemalloc2:i386
        echo "  [OK] jemalloc installed"
    fi
fi

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
echo "  mbii --update              Update MBII"
echo ""
echo "  Update MBII:  mbii --update"
echo "  or:           python3 manager.py --update"

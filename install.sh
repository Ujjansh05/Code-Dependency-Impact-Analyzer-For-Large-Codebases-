#!/usr/bin/env bash
# GraphXploit Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Ujjansh05/GraphXpolit/main/install.sh | bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "  ${CYAN}>${RESET} $1"; }
success() { echo -e "  ${GREEN}✔${RESET} $1"; }
fail()    { echo -e "  ${RED}✘${RESET} $1"; exit 1; }

echo ""
echo -e "${RED}${BOLD}"
cat << 'EOF'
   ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗██╗  ██╗██████╗ ██╗      ██████╗ ██╗████████╗
  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║╚██╗██╔╝██╔══██╗██║     ██╔═══██╗██║╚══██╔══╝
  ██║  ███╗██████╔╝███████║██████╔╝███████║ ╚███╔╝ ██████╔╝██║     ██║   ██║██║   ██║
  ██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║ ██╔██╗ ██╔═══╝ ██║     ██║   ██║██║   ██║
  ╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║██╔╝ ██╗██║     ███████╗╚██████╔╝██║   ██║
   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝   ╚═╝
EOF
echo -e "${RESET}"
echo -e "  ${BOLD}GraphXploit Installer${RESET}"
echo ""

# ── Check Python ────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    fail "Python 3.11+ is required but not found. Install it from https://python.org"
fi
success "Found $($PYTHON --version)"

# ── Check pip ───────────────────────────────────────────────────
if ! $PYTHON -m pip --version &>/dev/null; then
    fail "pip is not installed. Run: $PYTHON -m ensurepip --upgrade"
fi
success "pip available"

# ── Check Docker (optional) ─────────────────────────────────────
if command -v docker &>/dev/null; then
    success "Docker found ($(docker --version | head -c 30))"
else
    info "Docker not found. Install Docker to use 'graphxploit start'."
    info "https://docs.docker.com/get-docker/"
fi

# ── Install GraphXploit ─────────────────────────────────────────
echo ""
info "Installing GraphXploit..."

if command -v pipx &>/dev/null; then
    pipx install graphxploit-analyzer 2>/dev/null || \
    pipx install git+https://github.com/Ujjansh05/GraphXpolit.git 2>/dev/null || \
    $PYTHON -m pip install --user --break-system-packages git+https://github.com/Ujjansh05/GraphXpolit.git 2>/dev/null || \
    $PYTHON -m pip install --user git+https://github.com/Ujjansh05/GraphXpolit.git
    success "Installed via pipx (isolated environment)"
else
    $PYTHON -m pip install --user --break-system-packages git+https://github.com/Ujjansh05/GraphXpolit.git 2>/dev/null || \
    $PYTHON -m pip install --user git+https://github.com/Ujjansh05/GraphXpolit.git
    success "Installed via pip"
fi

# ── Verify ──────────────────────────────────────────────────────
echo ""
if command -v graphxploit &>/dev/null; then
    success "graphxploit is ready!"
    echo ""
    echo -e "  ${BOLD}Get started:${RESET}"
    echo -e "    graphxploit start          ${CYAN}# boot infrastructure${RESET}"
    echo -e "    graphxploit model mount    ${CYAN}# connect your LLM${RESET}"
    echo -e "    graphxploit analyze ./src  ${CYAN}# analyze a codebase${RESET}"
    echo ""
else
    info "Installed, but 'graphxploit' is not on your PATH."
    info "Add this to your shell profile:"
    echo ""
    SITE=$($PYTHON -m site --user-base)/bin
    echo "    export PATH=\"$SITE:\$PATH\""
    echo ""
fi

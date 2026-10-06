#!/usr/bin/env sh
# LMW installer for macOS/Linux.  One line:
#   curl -fsSL https://raw.githubusercontent.com/psinserver-jpg/localmodel-win/main/install.sh | sh
# Then type:  lmw
set -e
REPO="psinserver-jpg/localmodel-win"
BRANCH="${LMW_BRANCH:-main}"
DEST="${LMW_DIR:-$HOME/.local/share/lmw}"
BIN="$HOME/.local/bin"

echo "\n  LMW 설치 중…"
command -v python3 >/dev/null 2>&1 || { echo "  Python 3.8+ 이 필요합니다 (macOS: brew install python, Ubuntu: sudo apt install python3)"; exit 1; }

SELF_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/lmw/__main__.py" ]; then
  APP="$SELF_DIR"                      # running from a cloned folder
else
  APP="$DEST"
  if command -v git >/dev/null 2>&1; then
    if [ -d "$APP/.git" ]; then git -C "$APP" pull -q origin "$BRANCH"; else git clone -q -b "$BRANCH" "https://github.com/$REPO.git" "$APP"; fi
  else
    TMP="$(mktemp -d)"
    curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" | tar -xz -C "$TMP"
    rm -rf "$APP"; mkdir -p "$(dirname "$APP")"; mv "$TMP"/localmodel-win-* "$APP"; rm -rf "$TMP"
  fi
fi

# Claude-Code-style input box (optional; lmw works without it)
python3 -m pip install --user --quiet --disable-pip-version-check prompt_toolkit >/dev/null 2>&1 \
  || python3 -m pip install --user --quiet --break-system-packages prompt_toolkit >/dev/null 2>&1 || true

mkdir -p "$BIN"
cat > "$BIN/lmw" <<WRAP
#!/usr/bin/env sh
PYTHONPATH="$APP\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m lmw "\$@"
WRAP
chmod +x "$BIN/lmw"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) for rc in "$HOME/.profile" "$HOME/.bashrc" "$HOME/.zshrc"; do
       [ -f "$rc" ] || [ "$rc" = "$HOME/.profile" ] || continue
       grep -q '.local/bin' "$rc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
     done
     echo "  (새 터미널을 열어야 lmw 명령이 잡힙니다)";;
esac
# Ghostty: lmw opens in its own themed Ghostty window (https://ghostty.org)
if [ "$(uname)" = "Darwin" ]; then
  if [ ! -d /Applications/Ghostty.app ] && [ ! -d "$HOME/Applications/Ghostty.app" ]; then
    if command -v brew >/dev/null 2>&1; then
      echo "  Ghostty 설치 중 (brew)…"; brew install --cask ghostty >/dev/null 2>&1 || echo "  (Ghostty 설치 실패 — https://ghostty.org 에서 직접 설치하세요)"
    else
      echo "  Ghostty 를 쓰려면 https://ghostty.org 에서 설치하세요 (없으면 지금 터미널에서 실행됩니다)"
    fi
  fi
elif ! command -v ghostty >/dev/null 2>&1; then
  echo "  Ghostty 를 쓰려면 배포판 패키지로 설치하세요: https://ghostty.org/docs/install/binary (없으면 지금 터미널에서 실행됩니다)"
fi
echo "  ✔ 설치 완료!  lmw  를 입력하세요 (처음 실행 시 로그인 → 모델 설정)."

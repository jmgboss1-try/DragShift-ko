#!/bin/bash
# DragShift 한글판 맥 설치 / 업데이트 스크립트
# 터미널에서:
#   curl -fsSL https://raw.githubusercontent.com/jmgboss1-try/dragshift-ko/main/install-mac-ko.sh | bash
# 다시 실행하면 최신 버전으로 업데이트돼요. (설정은 그대로 유지)
set -euo pipefail
REPO="jmgboss1-try/dragshift-ko"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$HOME/.dragshift-ko"
APP="$HOME/Applications/DragShift 한글.app"

echo ""
echo "=== DragShift 한글판 설치 ==="

# 1) 파이썬 3.10 이상 찾기
PY=""
for c in /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 \
         /usr/local/bin/python3.13 /opt/homebrew/bin/python3.13 python3.13 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    PY="$(command -v "$c")"; break
  fi
done
if [ -z "$PY" ]; then
  echo "✗ 파이썬 3.10 이상을 찾지 못했어요. python.org에서 3.13을 설치한 뒤 다시 실행해 주세요."
  exit 1
fi
echo "→ 사용할 파이썬: $PY ($("$PY" --version))"

# 2) 최신 한글판 코드 내려받기
echo "→ 최신 한글판 내려받는 중"
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/main" -o "$TMP/src.tar.gz"
tar -xzf "$TMP/src.tar.gz" -C "$TMP"
SRC="$(find "$TMP" -maxdepth 1 -type d -iname 'dragshift-ko-*' | head -1)"
[ -d "$SRC/dragshift" ] || { echo "✗ 내려받은 파일이 이상해요."; exit 1; }
mkdir -p "$HOME_DIR"
rm -rf "$HOME_DIR/app"
mkdir -p "$HOME_DIR/app"
cp -R "$SRC/dragshift" "$SRC/requirements.txt" "$SRC/LICENSE" "$HOME_DIR/app/"

# 3) 필요한 부품 설치
if [ ! -x "$HOME_DIR/venv/bin/python" ]; then
  echo "→ 전용 환경 만드는 중"
  "$PY" -m venv "$HOME_DIR/venv"
fi
echo "→ 필요한 부품 내려받는 중 (처음엔 2~5분 걸려요)"
"$HOME_DIR/venv/bin/python" -m pip install --quiet --upgrade pip
"$HOME_DIR/venv/bin/python" -m pip install --quiet -r "$HOME_DIR/app/requirements.txt"

# 4) 실행용 앱 만들기
#    애플 실리콘 맥은 셸 스크립트로 된 앱을 바로 열지 못해서, AppleScript 앱(정식 실행 파일)으로 만듭니다.
echo "→ 'DragShift 한글' 앱 만드는 중"
RUN="$HOME_DIR/run.sh"
cat > "$RUN" <<SH
#!/bin/bash
export DRAGSHIFT_KO_LAUNCHER="$RUN"
cd "$HOME_DIR/app"
exec "$HOME_DIR/venv/bin/python" -m dragshift "\$@"
SH
chmod +x "$RUN"
rm -rf "$APP"
mkdir -p "$HOME/Applications"
osacompile -o "$APP" -e "do shell script quoted form of \"$RUN\" & \" > \" & quoted form of \"$HOME_DIR/last-run.log\" & \" 2>&1 &\""
cp "$HOME_DIR/app/dragshift/assets/dragshift.icns" "$APP/Contents/Resources/applet.icns"
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$APP/Contents/Info.plist" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier local.dragshift.ko" "$APP/Contents/Info.plist" 2>/dev/null || true
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
touch "$APP"

# 5) 영어판 종료 후 한글판 실행
echo "→ 영어판 DragShift 종료"
osascript -e 'quit app "DragShift"' >/dev/null 2>&1 || true
pkill -x DragShift >/dev/null 2>&1 || true
sleep 1
# 이미 켜져 있는 한글판(터미널에서 실행한 것 포함)도 종료
pkill -f "[-]m dragshift" >/dev/null 2>&1 || true
sleep 1
echo "→ 한글판 실행"
open "$APP"
sleep 4
if pgrep -f "[-]m dragshift" >/dev/null; then
  echo "✓ 한글판이 실행 중이에요."
else
  echo "✗ 한글판이 바로 꺼졌어요. 아래 내용을 Claude에게 보내주세요:"
  tail -20 "$HOME_DIR/last-run.log" 2>/dev/null || true
  tail -20 "$HOME/Library/Logs/DragShift/log.txt" 2>/dev/null || true
fi

echo ""
echo "✓ 완료! 메뉴 막대에 DragShift 아이콘이 생기면 성공이에요."
echo "  앱 위치: ~/Applications/DragShift 한글.app"

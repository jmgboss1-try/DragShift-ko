# DragShift 한글판

[DragShift](https://github.com/llamaboi55/DragShift)를 한국어로 쓰기 위해 고친 버전이에요.
파일을 **끌다가 Shift를 누르면** 커서 아래에 원형 메뉴가 열리고, 원하는 칸에 놓으면 변환·편집된 파일이 원본 옆에 저장돼요. 원본 파일은 바뀌지 않아요.

![미리보기](docs/preview.png)

## 원본과 달라진 점

- **한국어 화면** — 메뉴, 설정, 편집 창, 알림을 모두 한글로 표시해요 (`dragshift/ko.py`). 원본 코드는 거의 그대로 두고 화면에 그려지는 글자만 바꾸는 방식이라, 원본 업데이트를 합치기 쉬워요.
- **PDF → PPTX** — 변환 메뉴에 두 가지가 추가됐어요.
  - `PPTX` 모양 그대로: 페이지를 그림으로, 글자는 발표자 노트에.
  - `PPTX ✎` 글자 수정 가능: 배경은 그림으로, 글자는 원래 자리에 편집 가능한 텍스트 상자로.
- **글자 인식(OCR)** — 스캔한 PDF·사진의 글자를 읽어요 (`dragshift/ocr.py`). 인터넷 없이 컴퓨터 안에서만 처리해요.
  - 도구 메뉴 → `⌕ 글자 인식`: 검색·복사되는 PDF + TXT
  - 스캔본을 `TXT`나 `PPTX ✎`로 변환해도 자동으로 글자를 인식해요.
  - 맥: Apple Vision (macOS 13 이상에서 한국어) · 윈도우: Windows OCR (한국어 언어팩 필요)

## 설치

### 윈도우
[Releases](https://github.com/jmgboss1-try/dragshift-ko/releases/latest)에서 **DragShift-Setup.exe**를 받아 실행하세요. 관리자 권한은 필요 없어요.
- "Windows의 PC 보호" 창이 뜨면 **추가 정보 → 실행** (서명되지 않은 프로그램이라 뜨는 경고)
- 한국어 글자 인식: **설정 → 시간 및 언어 → 언어 및 지역**에 **한국어** 추가

### 맥
1. [python.org](https://www.python.org/downloads/macos/)에서 **Python 3.13**을 설치하고, 설치 후 열리는 폴더의 `Install Certificates.command`를 실행하세요.
2. 터미널에 붙여넣기:
   ```
   curl -fsSL https://raw.githubusercontent.com/jmgboss1-try/dragshift-ko/main/install-mac-ko.sh | bash
   ```
3. `~/Applications/DragShift 한글.app`이 만들어지고 메뉴 막대에 아이콘이 생겨요. 같은 명령을 다시 실행하면 최신 버전으로 업데이트돼요.

## 원본 업데이트 합치기

GitHub에서 **Sync fork** 버튼을 누르면 원본(llamaboi55/DragShift)의 변경 사항을 가져와요. 새로 생긴 영어 문구는 `dragshift/ko.py`의 `EXACT`/`RULES`에 번역을 추가하면 돼요.

## 라이선스

MIT — 원본 저작권은 [LICENSE](LICENSE)에 그대로 있어요. 원본 README는 [docs/README-original.md](docs/README-original.md)에 있어요.

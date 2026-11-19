"""DragShift 한글 패치.

앱 코드는 건드리지 않고, 화면에 글자가 그려지는 순간에만 영어를 한글로 바꿉니다.
(파일 형식 이름 PNG/JPG 등은 그대로 둡니다.)
"""
from __future__ import annotations

import re

# ── 그대로 바꾸는 문구 ────────────────────────────────────────────────
EXACT = {
    # 원형 메뉴 이름
    "Convert": "변환", "Tools": "도구", "Unsupported": "지원 안 함",
    "Drop here": "여기에 놓기", "Images · PDF · Word · Text": "이미지 · PDF · 워드 · 텍스트",
    "this file": "이 파일",
    # 도구 이름
    "Compress": "압축", "Resize": "크기 조절", "Crop": "자르기", "Edit": "보정",
    "Annotate": "표시하기", "Redact": "가리기", "Add BG": "배경 추가", "Metadata": "사진 정보",
    "Split": "나누기", "Rotate": "회전", "Merge": "합치기", "Protect": "암호 걸기",
    "Extract": "이미지 추출",
    # 도구 설명
    "Shrink file size": "용량 줄이기", "View · remove GPS": "위치정보 보기·삭제",
    "Hide private info": "개인정보 숨기기", "Trim to a ratio": "비율에 맞춰 자르기",
    "Light · colour · rotate": "밝기 · 색감 · 회전", "Arrows · text · steps": "화살표 · 글자 · 번호",
    "Gradient backdrop": "그라데이션 배경", "Change dimensions": "가로·세로 변경",
    "One PDF per page": "페이지별로 분리", "Turn pages 90°": "90도 돌리기",
    "Join into one PDF": "PDF 하나로 합치기", "Add a password": "비밀번호 설정",
    "Save embedded images": "들어있는 사진 저장",
    # 형식 설명
    "Small, universal": "작고 어디서나 열림", "Lossless · transparency": "무손실 · 투명 배경",
    "Smallest for web": "웹용 최소 용량", "iPhone format": "아이폰 사진 형식",
    "Print · archival": "인쇄 · 보관용", "Next-gen, tiny": "차세대 초소형", "Uncompressed": "무압축",
    "Document": "문서", "Windows icon": "윈도우 아이콘", "Legacy web": "옛날 웹 형식",
    "Editable Word": "편집 가능한 워드", "Plain text": "일반 텍스트",
    "Slides · exact look": "파워포인트 · 모양 그대로", "Slides · editable text": "파워포인트 · 글자 수정 가능", "This PDF has no pages.": "페이지가 없는 PDF예요.",
    # 메뉴 막대
    "Enabled": "켜기", "Open a file…": "파일 열기…", "Settings…": "설정…", "How to use": "사용법",
    "Tip the developer ♥": "개발자 후원하기 ♥", "Quit DragShift": "DragShift 종료",
    "Choose file(s) for DragShift": "DragShift로 처리할 파일 선택",
    # 알림창
    "Open": "열기", "Show in folder": "폴더에서 보기", "Show": "보기", "Undo": "되돌리기",
    "Undone": "되돌렸어요", "Working…": "처리 중…", "Couldn't finish": "완료하지 못했어요",
    "Compressing…": "압축 중…", "Splitting…": "나누는 중…", "Rotating…": "회전 중…",
    "Merging…": "합치는 중…", "Extracting images…": "이미지 추출 중…",
    "Compressed": "압축 완료", "Cropped": "자르기 완료", "Resized": "크기 조절 완료",
    "Edited": "보정 완료", "Background added": "배경 추가 완료", "Annotated": "표시 완료",
    "Redacted": "가리기 완료", "Metadata removed": "정보 삭제 완료", "Rotated 90°": "90도 회전 완료",
    "Password protected": "암호 설정 완료", "Nothing was written": "저장된 파일이 없어요",
    "same size": "용량 변화 없음", "already well compressed": "이미 충분히 압축됨",
    "burned into pixels": "완전히 지워짐", "private copy": "개인정보 없는 사본", "encrypted": "암호화됨",
    "DragShift is running": "DragShift 실행 중", "DragShift is already running": "DragShift가 이미 실행 중이에요",
    "The file was moved or deleted.": "파일이 옮겨졌거나 삭제됐어요.",
    "This file doesn't look like an image DragShift can read.": "DragShift가 읽을 수 없는 이미지예요.",
    "This PDF is password-protected. Remove the password first.": "암호가 걸린 PDF예요. 암호를 먼저 풀어주세요.",
    "No images found in this PDF.": "이 PDF에는 이미지가 없어요.",
    # 설정 · 사용법 창
    "Settings": "설정", "Done": "완료", "Got it": "알겠어요", "Welcome to DragShift": "DragShift 사용법",
    "Open the menu with": "메뉴 여는 키", "Save results": "결과 저장 위치",
    "Next to the original": "원본 옆에", "In a “DragShift” subfolder": "“DragShift” 하위 폴더에",
    "JPG / WebP quality": "JPG / WebP 화질", "PDF → image resolution": "PDF → 이미지 해상도",
    "Open at login": "로그인 시 자동 실행", "Open DragShift at login": "로그인할 때 DragShift 열기",
    "Enable full liquid glass…": "유리 효과 전체 켜기…", "Allow Screen Recording…": "화면 기록 허용…",
    "Lets the glass refract the windows behind it (Screen Recording permission)":
        "메뉴 뒤로 창이 비쳐 보이게 해요 (화면 기록 권한 필요)",
    "Start dragging any file": "파일을 끌기 시작하세요", "Drop it on a slice": "원하는 칸에 놓으세요",
    "in Finder or on the desktop": "Finder나 바탕화면에서",
    "the glass menu opens right under your cursor": "커서 아래에 원형 메뉴가 열려요",
    "the result is saved next to the original": "결과는 원본 옆에 저장돼요",
    "to switch between Convert and Tools": "변환 ↔ 도구 메뉴가 바뀌어요",
    "Shift ⇧": "Shift ⇧", "Control ⌃": "Control ⌃", "Option ⌥": "Option ⌥",
    # 편집 창 공통
    "Save": "저장", "Cancel": "취소", "Apply": "적용", "Reset": "초기화", "Confirm": "확인",
    "Copy": "복사", "Copied ✓": "복사됨 ✓", "Redo": "다시 실행", "Close (Esc)": "닫기 (Esc)",
    "Copy the result to the clipboard": "결과를 클립보드에 복사",
    "Hold to compare": "누르고 있으면 원본 비교", "Double-click the image to reset": "이미지를 더블클릭하면 초기화",
    "Original": "원본", "Original size": "원래 크기", "Size": "크기", "Pages": "페이지",
    # 자르기
    "Crop Image": "이미지 자르기", "Aspect ratio": "비율", "Free": "자유", "Cropping…": "자르는 중…",
    "Rotate 90°": "90도 회전",
    # 보정
    "Auto": "자동", "Automatic light and colour": "밝기·색감 자동 보정", "Applying edits…": "보정 적용 중…",
    "B&W": "흑백", "B&&W": "흑백",
    # 표시하기
    "Arrow": "화살표", "Text": "글자", "T Text": "T 글자", "Step": "번호", "Pen": "펜",
    "Rect": "사각형", "Ellipse": "원", "Highlight": "형광펜", "Type, then Enter": "입력 후 Enter",
    "Saving annotations…": "저장 중…",
    # 가리기
    "Black box": "검은 상자", "Blur": "흐리게", "Pixelate": "모자이크", "Redacting…": "가리는 중…",
    # 배경 추가
    "Background": "배경", "Background colour": "배경 색", "Custom colour": "직접 고르기",
    "Padding": "여백", "Corners": "모서리", "Shadow": "그림자", "Angle": "각도",
    "With Background": "배경 포함", "Save with Background": "배경 넣어 저장",
    "Adding background…": "배경 추가 중…",
    # 크기 조절 · 압축
    "Keep proportions": "비율 유지", "Exact size": "정확한 크기", "Resizing…": "크기 조절 중…",
    "Presets — percent or longest side in px": "빠른 선택 — 퍼센트 또는 긴 변 길이(px)",
    "Target size": "목표 용량", "Make each file under": "파일당 최대 용량",
    "Convert to WebP (usually the smallest)": "WebP로 변환 (보통 가장 작음)",
    "Already well compressed — try a smaller size or WebP": "이미 충분히 압축됐어요 — 더 작은 용량이나 WebP를 써보세요",
    # 사진 정보
    "Remove all metadata": "정보 전부 삭제", "Remove location only": "위치정보만 삭제",
    "Removing location…": "위치정보 삭제 중…", "Removing metadata…": "정보 삭제 중…",
    "No personal metadata found.": "개인정보가 들어있지 않아요.", "Open map": "지도 열기",
    "GPS removed, camera info kept": "위치정보만 지우고 카메라 정보는 유지",
    "Location": "위치", "No Location": "위치 없음", "Camera": "카메라", "Taken": "촬영일",
    "Dimensions": "해상도", "Software": "소프트웨어", "Exposure": "노출", "Aperture": "조리개",
    "Format": "형식", "Field": "항목", "Value": "값",
    # 글자 인식 (OCR)
    "OCR": "글자 인식", "Scan → searchable text": "스캔본 → 글자로", "Recognising text…": "글자 인식 중…",
    "Text recognised": "글자 인식 완료", "searchable": "검색 가능", "No text was found.": "글자를 찾지 못했어요.",
    "Text recognition isn't available on this computer yet.": "이 컴퓨터에서는 아직 글자 인식을 쓸 수 없어요.",
    "Text recognition failed on this Mac.": "이 맥에서 글자 인식에 실패했어요.",
    # 추가 문구
    "Quality": "화질", "Brightness": "밝기", "Contrast": "대비", "Saturation": "채도",
    "Sharpness": "선명도", "Warmth": "색온도", "⇋ Flip": "⇋ 좌우 반전", "⇵ Flip": "⇵ 상하 반전",
    "✦ Auto": "✦ 자동", "➜ Arrow": "➜ 화살표", "① Step": "① 번호", "▬ Marker": "▬ 형광펜",
    "◯ Circle": "◯ 동그라미",
    "Aurora": "오로라", "Dusk": "황혼", "Lemon": "레몬", "Mint": "민트", "Night": "밤하늘",
    "Ocean": "바다", "Peach": "복숭아", "Prism": "프리즘", "Rose": "장미", "Sunset": "노을",
    "150 dpi · small": "150 dpi · 작게", "200 dpi · balanced": "200 dpi · 보통",
    "300 dpi · print": "300 dpi · 인쇄용",
    "…pressed while you’re dragging a file": "…파일을 끄는 도중에 누르는 키",
    "Drag over anything you want hidden. It's burned into the pixels — it can't be undone in the copy.":
        "가릴 부분을 드래그하세요. 사본에서 완전히 지워져 되돌릴 수 없어요.",
    "in your file manager (Thunar, Nautilus…)": "파일 관리자에서",
    "in File Explorer or on the desktop": "파일 탐색기나 바탕화면에서",
    # 암호
    "Password-protect PDF": "PDF 암호 걸기", "Password": "비밀번호",
    "Passwords don't match yet.": "비밀번호가 서로 달라요.", "Use at least 4 characters.": "4자 이상 입력하세요.",
    "Encrypting…": "암호화 중…",
    "AES-256 encryption. Anyone opening the PDF will need this password.":
        "AES-256 암호화. PDF를 열려면 이 비밀번호가 필요해요.",
}

# ── 숫자·파일명이 들어가는 문구 ────────────────────────────────────────
RULES = [
    (r"Converting to (.+)…", r"\1(으)로 변환 중…"),
    (r"Combining (\d+) images…", r"이미지 \1개 합치는 중…"),
    (r"(\d+) images → 1 PDF", r"이미지 \1개 → PDF 1개"),
    (r"Couldn't open (.+)", lambda m: f"{tr(m[1])} 열기 실패"),
    (r"Can't convert (.+)", r"\1 파일은 변환할 수 없어요"),
    (r"(≈ )?(\d+)% smaller", r"\1\2% 줄어듦"),
    (r"(≈ )?(\d+)% larger", r"\1\2% 늘어남"),
    (r"Compressed (\d+) files", r"\1개 파일 압축 완료"),
    (r"(Cropped|Resized|Edited) (\d+) images", lambda m: f"이미지 {m[2]}개 {tr(m[1])}"),
    (r"Split into (\d+) PDFs", r"PDF \1개로 나눔"),
    (r"Merged (\d+) PDFs", r"PDF \1개 합침"),
    (r"Extracted (\d+) images?", r"이미지 \1개 추출"),
    (r"(\d+) pages?", r"\1쪽"),
    (r"(\d+) files", r"파일 \1개"),
    (r"Moved (\d+) files? to the (Trash|Recycle Bin)", r"파일 \1개를 휴지통으로 옮겼어요"),
    (r"Compress (\d+) files", r"파일 \1개 압축"),
    (r"Resize (\d+) files", r"파일 \1개 크기 조절"),
    (r"Show all (\d+) fields", r"항목 \1개 모두 보기"),
    (r"Looks good · (\w+) password", r"좋아요 · \1 비밀번호"),
    (r"Output  (.+) px  ·  PNG", r"결과  \1 px  ·  PNG"),
    (r"Max (\d+) px", r"최대 \1 px"),
    (r"Press (.+)", r"\1 키를 누르세요"),
    (r"Tap (.+) again", r"\1 키를 한 번 더 누르면"),
    (r"Drag any file, then press (.+)\.", r"파일을 끌다가 \1 키를 누르세요."),
    (r"Drag any file and press (.+)\. It lives in the tray\.", r"파일을 끌다가 \1 키를 누르세요. 메뉴 막대에 있어요."),
    (r"DragShift — press (.+) while dragging a file", r"DragShift — 파일을 끌면서 \1 키를 누르세요"),
    (r"DragShift (\S+)  ·  originals are never modified", r"DragShift \1  ·  원본은 절대 바뀌지 않아요"),
    (r"⇧ (.+)", lambda m: f"⇧ {tr(m[1])}"),
    (r"(.+) — DragShift", lambda m: f"{tr(m[1])} — DragShift"),
]
RULES = [(re.compile(p), r) for p, r in RULES]
LOWER = {k.lower(): v for k, v in EXACT.items()}


def tr(s):
    if not isinstance(s, str) or not s or s.isspace():
        return s
    if s in EXACT:
        return EXACT[s]
    if s.lower() in LOWER:            # 메뉴가 대문자로 그리는 경우 (COMPRESS 등)
        return LOWER[s.lower()]
    for rx, rep in RULES:
        m = rx.fullmatch(s)
        if m:
            return rep(m) if callable(rep) else m.expand(rep)
    if " · " in s:                     # "2.4 MB → 610 KB · quality 60" 같은 조합
        parts = s.split(" · ")
        out = [tr(x) for x in parts]
        if out != parts:
            return " · ".join(out)
    return s


def _wrap_first_str(cls, name):
    """화면에 보이는 글자(첫 번째 문자열 인자)만 번역. 뒤따르는 데이터 값은 건드리지 않음."""
    orig = getattr(cls, name)

    def f(self, *a, **k):
        a = list(a)
        for i, x in enumerate(a):
            if isinstance(x, str):
                a[i] = tr(x)
                break
        if "text" in k and isinstance(k["text"], str):
            k["text"] = tr(k["text"])
        return orig(self, *a, **k)
    setattr(cls, name, f)


def install():
    from PySide6 import QtGui, QtWidgets as W

    # 그리기·글자 폭 계산 모두 한글 기준으로 (레이아웃이 어긋나지 않게)
    for cls in (QtGui.QPainter,):
        _wrap_first_str(cls, "drawText")
    for cls in (QtGui.QFontMetrics, QtGui.QFontMetricsF):
        for n in ("horizontalAdvance", "elidedText", "boundingRect", "tightBoundingRect"):
            if hasattr(cls, n):
                _wrap_first_str(cls, n)
    for cls in (W.QLabel, W.QPushButton, W.QCheckBox, W.QRadioButton, W.QGroupBox, QtGui.QAction):
        _wrap_first_str(cls, "__init__")
    for cls, names in (
        (W.QLabel, ("setText",)), (W.QAbstractButton, ("setText",)), (QtGui.QAction, ("setText",)),
        (W.QMenu, ("addAction",)), (W.QWidget, ("setWindowTitle", "setToolTip")),
        (W.QComboBox, ("addItem", "setItemText")), (W.QLineEdit, ("setPlaceholderText",)),
        (W.QSystemTrayIcon, ("setToolTip",)), (W.QFileDialog, ("getOpenFileNames", "getOpenFileName")),
    ):
        for n in names:
            _wrap_first_str(cls, n)
    orig_items = W.QComboBox.addItems
    W.QComboBox.addItems = lambda self, items: orig_items(self, [tr(x) for x in items])


def boot():
    """Call before importing dragshift.app (both `python -m dragshift` and the frozen exe)."""
    import os
    import sys
    install()
    if sys.platform == "darwin" and os.environ.get("DRAGSHIFT_KO_LAUNCHER"):
        # 로그인 시 자동 실행이 한글판 실행기를 가리키도록
        from . import platform_mac
        platform_mac._program = lambda: [os.environ["DRAGSHIFT_KO_LAUNCHER"], "--quiet"]

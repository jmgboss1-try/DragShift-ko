; Inno Setup script — per-user install, no admin rights needed.
#define AppVersion GetEnv("DS_VERSION")
#if AppVersion == ""
  #define AppVersion "1.1.0"
#endif

[Setup]
AppId={{6C1E2B0A-7D5F-4E8B-9F3A-D7A5F1C2B3E4}
AppName=DragShift 한글판
AppVersion={#AppVersion}
AppPublisher=DragShift
DefaultDirName={localappdata}\Programs\DragShift
DefaultGroupName=DragShift
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=DragShift-Setup
SetupIconFile=..\dragshift\assets\dragshift.ico
UninstallDisplayIcon={app}\DragShift.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
#if FileExists(AddBackslash(CompilerPath) + "Languages\Korean.isl")
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
#else
Name: "korean"; MessagesFile: "Korean.isl"
#endif

[Tasks]
Name: "autostart"; Description: "윈도우에 로그인할 때 DragShift 자동 실행"; Flags: checkedonce
Name: "contextmenu"; Description: "파일 우클릭 메뉴에 ""DragShift"" 추가"; Flags: checkedonce
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; Flags: unchecked

[Files]
Source: "..\dist\DragShift\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\DragShift"; Filename: "{app}\DragShift.exe"
Name: "{autodesktop}\DragShift"; Filename: "{app}\DragShift.exe"; Tasks: desktopicon
Name: "{usersendto}\DragShift"; Filename: "{app}\DragShift.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DragShift"; ValueData: """{app}\DragShift.exe"" --quiet"; Tasks: autostart; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\*\shell\DragShift"; ValueType: string; ValueName: "MUIVerb"; ValueData: "DragShift…"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\DragShift"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\DragShift.exe"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\DragShift"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\DragShift\command"; ValueType: string; ValueName: ""; ValueData: """{app}\DragShift.exe"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\DragShift"; Flags: uninsdeletekey

[Run]
Filename: "{app}\DragShift.exe"; Description: "지금 DragShift 실행"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM DragShift.exe"; Flags: runhidden; RunOnceId: "KillDragShift"

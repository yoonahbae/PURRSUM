; PurrSum Noir - one-file installer. No admin rights needed; installs just for the current user.
Target amd64-unicode
SetCompressor /SOLID lzma
SetCompressorDictSize 64

!define APPNAME "PurrSum Noir"
!define VERSION "1.0.0"
!define LAUNCHER "$INSTDIR\python\PurrSum Noir.exe"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\PurrSumNoir"

Name "${APPNAME}"
OutFile "Install PurrSum Noir.exe"
InstallDir "$LOCALAPPDATA\Programs\${APPNAME}"
RequestExecutionLevel user
BrandingText "PurrSum Noir ${VERSION}"
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APPNAME}"
VIAddVersionKey "FileDescription" "PurrSum Noir installer"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "Yoonah"

!include "MUI2.nsh"
!define MUI_ICON "stage\purrsum.ico"
!define MUI_UNICON "stage\purrsum.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "welcome.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "welcome.bmp"
!define MUI_WELCOMEPAGE_TITLE "A tiny cat that adds up numbers"
!define MUI_WELCOMEPAGE_TEXT "PurrSum Noir puts a little cat on your screen. Click it, drag a box over any numbers (PDFs, emails, websites), and it adds them up and copies the total.$\r$\n$\r$\nEverything stays on this computer. Nothing is uploaded.$\r$\n$\r$\nClick Install to set it up. You'll need to be online for a minute while it downloads its number-reading part."
!define MUI_FINISHPAGE_TITLE "All set!"
!define MUI_FINISHPAGE_TEXT "There's a PurrSum Noir icon on your Desktop and in the Start menu.$\r$\n$\r$\nNext you'll pick your kitty and give it a name."
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Meet my kitty now"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchCat

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function LaunchCat
  Exec '"${LAUNCHER}" "$INSTDIR\app\purrsum.pyw"'
FunctionEnd

Section "Install"
  ; if an older cat is running, let it go home before replacing files
  nsExec::Exec 'taskkill /F /IM "PurrSum Noir.exe"'
  Sleep 500
  RMDir /r "$INSTDIR\app"
  SetOutPath "$INSTDIR"
  File "stage\purrsum.ico"
  File /r "stage\app"
  File /r "stage\python"

  ; the number-reading engine is downloaded once from the official Python package site
  ; (pinned versions, every file fingerprint-checked), so this installer stays small
  DetailPrint "Setting up the number-reading engine (about 90 MB download)..."
  engine:
  nsExec::ExecToLog '"$INSTDIR\python\python.exe" -u "$INSTDIR\app\purrsum\setup_engine.py" --if-needed'
  Pop $0
  StrCmp $0 "0" engine_ok
  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "PurrSum Noir couldn't download its number-reading part.$\r$\n$\r$\nPlease check that you're connected to the internet, then click Retry." IDRETRY engine
  DetailPrint "The number-reading part isn't set up yet. Run this installer again when you're online."
  engine_ok:

  SetOutPath "$INSTDIR"
  CreateShortcut "$DESKTOP\${APPNAME}.lnk" "${LAUNCHER}" '"$INSTDIR\app\purrsum.pyw"' "$INSTDIR\purrsum.ico" 0 SW_SHOWNORMAL "" "Call your PurrSum cat"
  CreateShortcut "$SMPROGRAMS\${APPNAME}.lnk" "${LAUNCHER}" '"$INSTDIR\app\purrsum.pyw"' "$INSTDIR\purrsum.ico" 0 SW_SHOWNORMAL "" "Call your PurrSum cat"

  WriteUninstaller "$INSTDIR\Uninstall PurrSum Noir.exe"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayName" "${APPNAME}"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINSTKEY}" "Publisher" "Yoonah"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\purrsum.ico"
  WriteRegStr HKCU "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "UninstallString" '"$INSTDIR\Uninstall PurrSum Noir.exe"'
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  nsExec::Exec 'taskkill /F /IM "PurrSum Noir.exe"'
  Sleep 500
  Delete "$DESKTOP\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}.lnk"
  RMDir /r "$INSTDIR\app"
  RMDir /r "$INSTDIR\python"
  Delete "$INSTDIR\purrsum.ico"
  Delete "$INSTDIR\Uninstall PurrSum Noir.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "${UNINSTKEY}"
SectionEnd

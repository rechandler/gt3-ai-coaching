; GT3 AI Coaching - Windows Installer Script
; Uses NSIS (Nullsoft Scriptable Install System)

!define APP_NAME "GT3 AI Coaching"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "GT3 Racing Solutions"
!define APP_URL "https://github.com/rechandler/gt3-ai-coaching"
!define APP_EXECUTABLE "GT3AICoaching.exe"
!define APP_DESCRIPTION "Real-time AI coaching for GT3 racing in iRacing"

; Modern UI
!include "MUI2.nsh"
!include "FileFunc.nsh"

; General
Name "${APP_NAME}"
OutFile "GT3-AI-Coaching-Setup-v${APP_VERSION}.exe"
Unicode True
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" ""
RequestExecutionLevel admin

; Variables
Var StartMenuFolder

; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "header.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP "wizard.bmp"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY

; Start Menu Folder Page Configuration
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\${APP_NAME}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Version Information
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription" "${APP_DESCRIPTION}"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "LegalCopyright" "© 2025 ${APP_PUBLISHER}"

; Installer Sections
Section "GT3 AI Coaching (required)" SecMain
  SectionIn RO
  
  ; Set output path to the installation directory
  SetOutPath $INSTDIR
  
  ; Install main application files
  File /r "..\build\*.*"
  
  ; Create Python server directory
  SetOutPath "$INSTDIR\python-server"
  File /r "..\python-server\*.*"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  ; Store installation folder
  WriteRegStr HKCU "Software\${APP_NAME}" "" $INSTDIR
  
  ; Create registry entries for Add/Remove Programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\${APP_EXECUTABLE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_URL}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1
  
  ; Get installed size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "EstimatedSize" "$0"
  
SectionEnd

Section "Desktop Shortcut" SecDesktop
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXECUTABLE}" "" "$INSTDIR\${APP_EXECUTABLE}" 0
SectionEnd

Section "Start Menu Shortcuts" SecStartMenu
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\${APP_NAME}.lnk" "$INSTDIR\${APP_EXECUTABLE}" "" "$INSTDIR\${APP_EXECUTABLE}" 0
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

; Section Descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "Installs the main GT3 AI Coaching application and Python telemetry server."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Creates a shortcut on the desktop for easy access."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Creates shortcuts in the Start Menu."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Uninstaller Section
Section "Uninstall"
  ; Remove files and directories
  RMDir /r "$INSTDIR"
  
  ; Remove shortcuts
  Delete "$DESKTOP\${APP_NAME}.lnk"
  
  ; Remove Start Menu folder
  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
  Delete "$SMPROGRAMS\$StartMenuFolder\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
  RMDir "$SMPROGRAMS\$StartMenuFolder"
  
  ; Remove registry entries
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey /ifempty HKCU "Software\${APP_NAME}"
  
SectionEnd

; Functions
Function .onInit
  ; Check if already installed
  ReadRegStr $R0 HKCU "Software\${APP_NAME}" ""
  StrCmp $R0 "" done
  
  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
  "${APP_NAME} is already installed. $\n$\nClick 'OK' to remove the previous version or 'Cancel' to cancel this upgrade." \
  IDOK uninst
  Abort
  
  uninst:
    ClearErrors
    ExecWait '$R0\Uninstall.exe _?=$R0'
    
    IfErrors no_remove_uninstaller done
    IfFileExists "$R0\Uninstall.exe" 0 done
    Delete $R0\Uninstaller.exe
    RMDir $R0
    
  no_remove_uninstaller:
  done:
FunctionEnd

Unicode True
ManifestDPIAware True
RequestExecutionLevel user

!ifndef APP_NAME
  !error "APP_NAME is required"
!endif

!ifndef APP_VERSION
  !error "APP_VERSION is required"
!endif

!ifndef SOURCE_DIR
  !error "SOURCE_DIR is required"
!endif

!ifndef OUTPUT_FILE
  !error "OUTPUT_FILE is required"
!endif

!ifndef MAIN_EXE
  !error "MAIN_EXE is required"
!endif

!ifndef INSTALL_DIR_NAME
  !define INSTALL_DIR_NAME "${APP_NAME}"
!endif

!define APP_ID "MistRelayDesktopQt"

Name "${APP_NAME}"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\${INSTALL_DIR_NAME}"
InstallDirRegKey HKCU "Software\${APP_ID}" "InstallDir"
ShowInstDetails show
ShowUnInstDetails show

!macro CloseRunningApp
  ClearErrors
  ExecWait '"$SYSDIR\taskkill.exe" /IM "${MAIN_EXE}" /T /F' $0
  Sleep 1000
!macroend

Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
  !insertmacro CloseRunningApp
  SetOutPath "$INSTDIR"
  RMDir /r "$INSTDIR"
  File /r "${SOURCE_DIR}\*.*"

  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${MAIN_EXE}"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${MAIN_EXE}"

  WriteRegStr HKCU "Software\${APP_ID}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "Publisher" "MistRelay"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayIcon" "$INSTDIR\${MAIN_EXE}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "NoRepair" 1
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  !insertmacro CloseRunningApp
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "Software\${APP_ID}"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"
SectionEnd

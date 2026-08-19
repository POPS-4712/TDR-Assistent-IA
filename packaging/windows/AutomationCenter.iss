#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef AppArchitecture
  #define AppArchitecture "x64"
#endif
#ifndef SourceRoot
  #define SourceRoot "."
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

#define AppName "Automation Center"
#define AppPublisher "Automation Center"
#define AppExeName "AutomationCenter.exe"

[Setup]
AppId={{6F6A9127-0623-4F1F-9A95-E1BC2AB249DE}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Automation Center
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=AutomationCenter-{#AppVersion}-win-{#AppArchitecture}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
ArchitecturesAllowed={#if AppArchitecture == "arm64"}arm64{#else}x64compatible{#endif}
ArchitecturesInstallIn64BitMode={#if AppArchitecture == "arm64"}arm64{#else}x64compatible{#endif}

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".env,.git\*,dist\*,postgres-data\*,.n8n\*,*.log"

[Icons]
Name: "{group}\Automation Center"; Filename: "{app}\{#AppExeName}"; Parameters: "start"
Name: "{autodesktop}\Automation Center"; Filename: "{app}\{#AppExeName}"; Parameters: "start"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Parameters: "init"; Flags: runhidden waituntilterminated
Filename: "{app}\{#AppExeName}"; Parameters: "start"; Description: "Start Automation Center"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{app}\{#AppExeName}"; Parameters: "stop"; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{app}\{#AppExeName}"; Parameters: "remove-data --confirm-remove-data"; Flags: runhidden waituntilterminated skipifdoesntexist; Check: ShouldRemoveUserData

[Code]
var
  RemoveUserData: Boolean;

function InitializeUninstall(): Boolean;
begin
  { Silent uninstallations must never block or delete private data without a visible confirmation. }
  if UninstallSilent() then
    RemoveUserData := False
  else
    RemoveUserData := MsgBox('Remove Automation Center user data, including local configuration and the local service data volumes? This cannot be undone.', mbConfirmation, MB_YESNO) = IDYES;
  Result := True;
end;

function ShouldRemoveUserData(): Boolean;
begin
  Result := RemoveUserData;
end;

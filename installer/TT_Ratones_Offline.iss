#define MyAppName "TT Ratones 2026"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ESCOM - IPN"
#define MyAppExeName "launcher.vbs"
#ifndef Acceleration
  #define Acceleration "cpu"
#endif
#if Acceleration == "nvidia"
  #define MyOutputName "TT_Ratones_2026_Offline_NVIDIA_Setup"
#else
  #define MyOutputName "TT_Ratones_2026_Offline_CPU_Setup"
#endif

[Setup]
AppId={{B17D26F1-A2F7-4D51-A725-7E0877692E15}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\TT_Ratones_2026
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename={#MyOutputName}
Compression=lzma2/fast
SolidCompression=yes
#if Acceleration == "nvidia"
DiskSpanning=yes
DiskSliceSize=max
#endif
WizardStyle=modern
SetupLogging=yes
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador offline de {#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
Source: "b\p\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\{#MyAppExeName}"""; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\{#MyAppExeName}"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autoprograms}\{#MyAppName} - Diagnostico"; Filename: "{app}\validar_instalacion.bat"; WorkingDir: "{app}"

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\{#MyAppExeName}"""; WorkingDir: "{app}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent

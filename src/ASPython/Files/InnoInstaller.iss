;TODO:
;Get the 'launch now' working (checkbox at the end of install)
;Figure out how to disconnect the file device upon uninstall.

;########################################################
; General (common) fields
;########################################################
[Setup]
AppId={#AppGUID}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={commonpf64}\{#AppPublisher}\{#AppName}
DefaultGroupName={#AppPublisher}\{#AppName}
AllowNoIcons=yes
DisableDirPage=yes
OutputBaseFilename={#AppName}_Setup_{#AppVersion}
Compression=lzma
SolidCompression=yes
AlwaysShowDirOnReadyPage=yes
AlwaysShowGroupOnReadyPage=yes
DisableWelcomePage=no
;TODO: look into these directives:
;WizardImageFile=myimage.bmp
;SetupIconFile=
;BackColor=clBlue
;BackColor2=clBlack
;Custom icons? 

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"


;########################################################
; ARsim simulator fields
;########################################################
#if IncludeSimulator == "yes"
    
    #define AppExeName "ar000loader.exe"

    [Components]
    Name: "Simulator"; Description: "ARsim simulator"; Types: full compact custom;

    [Files]
    Source: {#SimulationDirectory}\*; DestDir: "{app}\ARsim"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: Simulator;

    [Icons]
    ;Start Menu shortcuts
    Name: "{group}\{#AppName} Simulator"; Filename: "{app}\ARsim\{#AppExeName}"; Components: Simulator
    ;Desktop shortcuts
    Name: "{commondesktop}\{#AppName}\{#AppName} Simulator"; Filename: "{app}\ARsim\{#AppExeName}"; Tasks: desktopicon

    [Run]
    ;Start up ARsim if checked to do so
    Filename: "{app}\ARsim\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent; Components: Simulator;

    [Registry]
    ;Need to write to the registry to run ar000loader as admin, otherwise the ARsim will not boot in Program Files/(x86)
    ;Write to win7 64bit reg only if running windows7 64bit
    Root: "HKLM64"; Subkey: "SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers\"; ValueType: String; ValueName: "{app}\ARsim\ar000loader.exe"; ValueData: "RUNASADMIN"; Flags: uninsdeletekeyifempty uninsdeletevalue; MinVersion: 6.1.7601; Check: IsWin64; Components: Simulator;
    ;Write to win7 32bit reg only if running windows7 32bit
    Root: "HKLM32"; Subkey: "SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers\"; ValueType: string; ValueName: "{app}\ARsim\ar000loader.exe"; ValueData: "RUNASADMIN"; Flags: uninsdeletekeyifempty uninsdeletevalue; MinVersion: 6.1.7601; Check: NOT IsWin64; Components: Simulator;

#endif


;########################################################
; HMI fields
;########################################################
#if IncludeHmi == "yes"

    [Components]
    Name: "HMI"; Description: "webHMI user interface"; Types: full custom;

    [Files]
    Source: {#HMIDirectory}\*; DestDir: "{app}\HMI"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: HMI;

    [Icons]
    ;Start Menu shortcuts
    Name: "{group}\{#AppName} HMI"; Filename: "{app}\HMI\{#HMIExeName}"; Components: HMI
    ;Desktop shortcuts
    Name: "{commondesktop}\{#AppName}\{#AppName} HMI"; Filename: "{app}\HMI\{#HMIExeName}"; Tasks: desktopicon

#endif


;########################################################
; User partition fields
;########################################################
#if IncludeUserPartition == "yes"

    [Components]
    Name: "UserPartition"; Description: "Recipe data"; Types: full custom;

    [Files]
    Source: {#UserPartitionDirectory}\*; DestDir: "{app}\UserPartition"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: UserPartition;
    Source: {#UserPartitionDirectory}\{#JunctionBatchFilename}; DestDir:"{app}\UserPartition"; Components: UserPartition; Permissions: everyone-full;  
    Source: DisconnectFileDevice.bat; Destdir: "{app}"; Components: UserPartition;

    [Run]
    ;Create Folder Junction in User Partition (C:\ARSimUser) and link it to Application's User Partition (C:\Program Files\Publisher\AppName\User Partition\Config)
    Filename: "{app}\UserPartition\{#JunctionBatchFilename}"; Components: UserPartition;

    ; [UninstallRun]
    ; ;Remove the symlink to user partition that was created.
    ; Filename: "{app}\DisconnectFileDevice.bat"; Parameters:"{#AppPublisher}-{#AppName}"; Components: UserPartition;

#endif



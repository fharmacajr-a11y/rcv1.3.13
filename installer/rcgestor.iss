; =============================================================================
; RC Gestor de Clientes - Inno Setup Script
; =============================================================================
; Script para geração do instalador Windows.
;
; Uso:
;   1. Abra este arquivo no Inno Setup Compiler
;   2. Compile (Build > Compile ou Ctrl+F9)
;   3. O instalador será gerado em installer/Output/
;
; Pré-requisitos:
;   - Executável já gerado via PyInstaller (pyinstaller rcgestor.spec)
;   - Inno Setup 6.x instalado (https://jrsoftware.org/isdl.php)
;
; Revisado na FASE 4 (2025-12-02) - Documentação e organização do build.
; =============================================================================

; -----------------------------------------------------------------------------
; DEFINIÇÕES DE VERSÃO E NOMES
; -----------------------------------------------------------------------------
#define MyAppName "RC Gestor de Clientes"
#define MyAppVersion "1.3.92"
#define MyAppPublisher "RC Apps"
#define MyAppURL "https://github.com/fharmacajr-a11y/rcv1.3.13"
#define MyAppExeName "RC-Gestor-Clientes-1.3.92.exe"
#define MyAppCopyright "© 2025 RC Apps. Todos os direitos reservados."

; -----------------------------------------------------------------------------
; CONFIGURAÇÃO PRINCIPAL
; -----------------------------------------------------------------------------
[Setup]
; Identificador único do aplicativo (GUID)
; IMPORTANTE: Não altere este GUID após a primeira publicação!
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}

; Informações do aplicativo
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppCopyright={#MyAppCopyright}

; Diretórios de instalação
DefaultDirName={autopf}\RC Gestor
DefaultGroupName={#MyAppName}

; Permissões (requer admin para instalar em Program Files)
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Configurações de saída
OutputDir=Output
OutputBaseFilename=RC-Gestor-Setup-{#MyAppVersion}
SetupIconFile=..\rc.ico

; Compressão
Compression=lzma2/max
SolidCompression=yes

; Interface do instalador
WizardStyle=modern
WizardSizePercent=100

; Informações de versão do instalador
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador do {#MyAppName}
VersionInfoCopyright={#MyAppCopyright}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; Arquitetura
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Desinstalação
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; -----------------------------------------------------------------------------
; IDIOMAS
; -----------------------------------------------------------------------------
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; -----------------------------------------------------------------------------
; TAREFAS (opções durante instalação)
; -----------------------------------------------------------------------------
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

; -----------------------------------------------------------------------------
; ARQUIVOS A INSTALAR
; -----------------------------------------------------------------------------
[Files]
; Executável principal (gerado pelo PyInstaller)
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Arquivos adicionais (descomente conforme necessário)
; Source: "..\dist\*.dll"; DestDir: "{app}"; Flags: ignoreversion
; Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
; Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

; NOTA: Como usamos onefile no PyInstaller, apenas o .exe é necessário.
; Se mudar para onedir, descomente as linhas acima e ajuste os caminhos.

; -----------------------------------------------------------------------------
; ÍCONES (atalhos)
; -----------------------------------------------------------------------------
[Icons]
; Atalho no Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Atalho na Área de Trabalho (se selecionado)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Atalho no Quick Launch (se selecionado)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

; -----------------------------------------------------------------------------
; AÇÕES PÓS-INSTALAÇÃO
; -----------------------------------------------------------------------------
[Run]
; Opção para executar o aplicativo após instalação
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; -----------------------------------------------------------------------------
; REGISTRO DO WINDOWS (opcional)
; -----------------------------------------------------------------------------
[Registry]
; Adiciona entrada no registro para identificar instalação
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey

; -----------------------------------------------------------------------------
; CÓDIGO PASCAL (scripts customizados)
; -----------------------------------------------------------------------------
[Code]
// Verifica se há versão anterior instalada
function InitializeSetup(): Boolean;
var
  UninstallKey: String;
  UninstallString: String;
begin
  Result := True;

  // Verifica instalação anterior
  UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1';
  if RegQueryStringValue(HKLM, UninstallKey, 'UninstallString', UninstallString) then
  begin
    if MsgBox('Uma versão anterior do {#MyAppName} foi detectada.' + #13#10 +
              'Deseja desinstalar a versão anterior antes de continuar?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Executa desinstalador silenciosamente
      Exec(RemoveQuotes(UninstallString), '/SILENT', '', SW_SHOW, ewWaitUntilTerminated, Result);
    end;
  end;
end;

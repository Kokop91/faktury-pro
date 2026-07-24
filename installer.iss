; Skrypt instalatora Windows (Faza 18C, Etap 3 - patrz ETAP_3_ROZWOJU.md)
; laczacy w jeden plik: pliki spakowane przez PyInstaller (Faza 18A) razem
; z dolaczonymi binariami prywatnego PostgreSQL (Faza 18B - dolaczonymi do
; dist/Faktury Pro/_internal/vendor/postgresql/pgsql/ recznym kopiowaniem
; PO zbudowaniu, patrz scripts/dolacz_postgres_do_buildu.py i komentarz w
; faktury_pro.spec - PyInstaller nigdy nie widzi tych plikow, wiec Inno Setup
; (ktory po prostu pakuje caly gotowy folder dist/Faktury Pro) tez ich po
; prostu bierze razem z reszta, bez dodatkowej pracy).
;
; NARZEDZIE: Inno Setup (nie NSIS) - uzasadnienie: projekt jest w Pascal
; Script (czytelniejszy i lepiej udokumentowany niz jezyk skryptowy NSIS do
; potrzebnej tu logiki [Code] - pytanie o zachowanie danych przy deinstalacji
; z rozroznieniem trybu cichego/interaktywnego), ma wbudowane, deklaratywne
; wsparcie dla instalacji per-uzytkownik bez uprawnien administratora
; (PrivilegesRequired=lowest) bez dodatkowych obejsc, i jest szeroko uzywany
; do dokladnie tego typu dystrybucji (spakowana appka Python + zasoby).
;
; BUDOWANIE:
;     "C:\Tools\InnoSetup6\ISCC.exe" installer.iss
; (albo dowolna inna instalacja Inno Setup 6 - ISCC.exe to jego kompilator
; wiersza polecen). Zaklada, ze dist/Faktury Pro/ juz istnieje i zawiera
; binaria PostgreSQL (patrz BUDOWANIE w faktury_pro.spec - najpierw
; pyinstaller, potem scripts/dolacz_postgres_do_buildu.py, DOPIERO potem to).
;
; Wynik: Output/FakturyPro-Setup-{wersja z AppWersja ponizej}.exe

#define AppNazwa "Faktury Pro"
#define AppWersja "1.1.4"
#define AppWydawca "Faktury Pro"
#define AppExeNazwa "Faktury Pro.exe"

[Setup]
AppId={{D003A2E8-B85A-4057-9E62-F581B95DDC84}
AppName={#AppNazwa}
AppVersion={#AppWersja}
AppVerName={#AppNazwa} {#AppWersja}
AppPublisher={#AppWydawca}
VersionInfoVersion={#AppWersja}

; Instalacja per-uzytkownik, BEZ wymogu uprawnien administratora (punkt 2
; zakresu Fazy 18C) - "lowest" oznacza, ze instalator nigdy nie prosi o
; podniesienie uprawnien (UAC), nawet jesli uruchomi go administrator.
PrivilegesRequired=lowest
; Katalog domyslny w profilu uzytkownika (NIE Program Files) - ten sam wzorzec
; co np. VS Code czy inne nowoczesne instalatory per-uzytkownik na Windows.
DefaultDirName={localappdata}\Programs\FakturyPro
DefaultGroupName={#AppNazwa}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir=Output
OutputBaseFilename=FakturyPro-Setup-{#AppWersja}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeNazwa}

Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern

; Appka jest nadal uruchomiona przy probie reinstalacji/aktualizacji -
; Inno Setup sam poprosi o zamkniecie zamiast cicho nadpisywac pliki w uzyciu.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Cala zawartosc dist/Faktury Pro/ (GUI + backend + WeasyPrint + matplotlib +
; prywatny PostgreSQL) - rekurencyjnie, bez zadnych wykluczen, dokladnie tak
; jak zbudowal to PyInstaller + skrypt dolaczajacy Postgresa.
Source: "dist\Faktury Pro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppNazwa}"; Filename: "{app}\{#AppExeNazwa}"
Name: "{group}\{cm:UninstallProgram,{#AppNazwa}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppNazwa}"; Filename: "{app}\{#AppExeNazwa}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeNazwa}"; Description: "{cm:LaunchProgram,{#StringChange(AppNazwa, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Katalog z DANYMI appki (Faza 18B) - prywatna baza PostgreSQL, hash hasla,
// token KSeF, ustawienia. CELOWO POZA katalogiem instalacji (ktory jest w
// profilu uzytkownika pod Programs, wiec normalny deinstalator go i tak
// usuwa) - LOCALAPPDATA/FakturyPro, zeby przetrwal odinstalowanie/aktualizacje,
// chyba ze uzytkownik WYRAZNIE zgodzi sie go usunac ponizej.
function KatalogDanych(): String;
begin
  Result := ExpandConstant('{localappdata}\FakturyPro');
end;

// Zamyka wszelkie procesy uruchomione Z KATALOGU INSTALACJI - glowny GUI i/lub
// osierocony prywatny PostgreSQL (Faza 18B), ktory mogl zostac uruchomiony bez
// czystego zamkniecia appki (np. awaryjne zakonczenie procesu, awaria appki) -
// bez tego pliki .dll/.exe w uzyciu blokuja usuwanie/nadpisywanie katalogu
// instalacji (zweryfikowane empirycznie: symulacja awaryjnego zamkniecia
// zostawiala osierocony postgres.exe blokujacy 16 plikow przy deinstalacji).
// Filtrowanie po SCIEZCE PLIKU wykonywalnego (nie po samej nazwie "postgres.exe"),
// zeby NIGDY nie tkac innego, niezwiazanego Postgresa gdzie indziej na komputerze.
procedure ZatrzymajProcesyAppki();
var
  ResultCode: Integer;
  Polecenie: String;
begin
  Polecenie :=
    'Get-CimInstance Win32_Process | ' +
    'Where-Object { $_.ExecutablePath -like ''' + ExpandConstant('{app}') + '\*'' } | ' +
    'ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }';
  Exec('powershell.exe', '-NoProfile -Command "' + Polecenie + '"', '',
    SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1000);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Odpowiedz: Integer;
begin
  if CurUninstallStep = usUninstall then
    ZatrzymajProcesyAppki();

  if CurUninstallStep = usPostUninstall then
  begin
    if DirExists(KatalogDanych()) then
    begin
      { Deinstalacja cicha/automatyczna (np. wdrozenie firmowe, msiexec-owy
        skrypt) NIGDY nie usuwa danych bez pytania - bezpieczny domyslny wybor
        to ZACHOWAJ, zgodnie z zakresem Fazy 18C. Interaktywne pytanie nizej
        pojawia sie WYLACZNIE przy zwyklej, recznej deinstalacji. }
      if UninstallSilent() then
        Exit;

      { MB_DEFBUTTON2 = fokus domyslnie na "Nie" - Enter/Esc zachowuje dane,
        trzeba SWIADOMIE kliknac "Tak", zeby je usunac. Nieodwracalne
        usuniecie danych firmowych (wystawionych faktur) bez wyraznej zgody
        byloby zbyt ryzykowne, zeby zrobic to domyslnie. }
      Odpowiedz := MsgBox(
        'Czy chcesz usunąć również dane aplikacji Faktury Pro?' + #13#10 + #13#10 +
        'Obejmuje to bazę danych ze wszystkimi wystawionymi fakturami, dokumentami ' +
        'magazynowymi i ustawieniami (hasło, token KSeF).' + #13#10 + #13#10 +
        'Katalog: ' + KatalogDanych() + #13#10 + #13#10 +
        'Wybierz "Nie", jeśli planujesz ponownie zainstalować aplikację i chcesz ' +
        'zachować swoje dane - to jest bezpieczny, zalecany wybór.',
        mbConfirmation, MB_YESNO or MB_DEFBUTTON2
      );
      if Odpowiedz = IDYES then
        DelTree(KatalogDanych(), True, True, True);
    end;
  end;
end;

// To samo zabezpieczenie co przy deinstalacji (patrz ZatrzymajProcesyAppki
// powyzej), zeby reinstalacja/aktualizacja nad osieroconym prywatnym
// Postgresem tez sie nie wywalila na plikach w uzyciu.
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  ZatrzymajProcesyAppki();
  Result := '';
end;

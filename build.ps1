# Builds the B1 unified build of PersonalCleaner (free + Pro in one exe).
# Licensing is BUNDLED (COMMERCIAL=True) so free users see locked Pro features
# (A2/A3/P1/P2) and can unlock them with a key. No more --exclude-module.
# Run from the project folder:  .\build.ps1
$ErrorActionPreference = "Stop"

$py = "C:\laragon\bin\python\python-3.10\python.exe"
if (-not (Test-Path $py)) {
    $py = "python"
}

Write-Host "Using Python: $py"
& $py -m pip install --quiet psutil pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

& $py -m pip install --quiet PyQt6
& $py -m PyInstaller --noconfirm --clean --onefile --name PersonalCleaner --windowed --icon icon.ico --noupx --version-file version_info.txt --add-data "icon.ico;." --add-data "LICENSE;." --paths commercial --hidden-import licensing --hidden-import PyQt6.QtCore --hidden-import PyQt6.QtWidgets --hidden-import PyQt6.QtGui --hidden-import PyQt6.QtNetwork gui.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

Write-Host ""
Write-Host "Build done: dist\PersonalCleaner.exe (gated - Pro features need a key)"
Write-Host "Remember to run it through VirusTotal before shipping."

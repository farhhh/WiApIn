# Проверка прав администратора
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ОШИБКА: Запустите скрипт от имени администратора!" -ForegroundColor Red
    exit
}

$paths = @(
    "C:\Program Files",
    "C:\Program Files (x86)",
    "C:\Users",
    "C:\ProgramData\Autodesk",
    "C:\Autodesk",
    "C:\autodesk",
    "C:\Windows",
    "C:\ProgramData\Package Cache",
    "$env:TEMP"
)

Write-Host "--- Добавление исключений в Windows Defender ---" -ForegroundColor Cyan

foreach ($path in $paths) {
    try {
        Add-MpPreference -ExclusionPath $path -ErrorAction Stop
        Write-Host "[OK] Добавлено: $path" -ForegroundColor Green
    } catch {
        Write-Host "[!] Ошибка при добавлении: $path (возможно, уже есть)" -ForegroundColor Yellow
    }
}

Write-Host "`nГотово! Перезагрузка не требуется." -ForegroundColor Cyan

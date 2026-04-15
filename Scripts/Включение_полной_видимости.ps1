Write-Host "--- Настройка Проводника (Win 10/11) ---" -ForegroundColor Cyan

# 1. Показать расширения имен файлов
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "HideFileExt" -Value 0

# 2. Показать скрытые файлы, папки и диски
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "Hidden" -Value 1

# 3. Включить поддержку длинных путей (важно для Unreal Engine и глубоких папок проектов)
$longPathsPath = "HKLM:\System\CurrentControlSet\Control\FileSystem"
if (-not (Test-Path $longPathsPath)) {
    New-Item -Path $longPathsPath -Force
}
Set-ItemProperty -Path $longPathsPath -Name "LongPathsEnabled" -Value 1

# 4. Отключить "Поиск в интернете" в меню Пуск (ускоряет локальный поиск)
$searchPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search"
Set-ItemProperty -Path $searchPath -Name "BingSearchEnabled" -Value 0

Write-Host "Обновление интерфейса..." -ForegroundColor Yellow

# Перезапуск проводника, чтобы применить настройки мгновенно
Stop-Process -Name explorer -Force

Write-Host "[OK] Настройки применены! Расширения и скрытые файлы теперь видны." -ForegroundColor Green

Write-Host "Настройка Проводника..." -ForegroundColor Cyan

# Показать расширения файлов
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "HideFileExt" -Value 0
# Показать скрытые файлы
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "Hidden" -Value 1
# Включить длинные пути (больше 260 символов)
New-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

Write-Host "[OK] Проводник настроен: расширения и пути исправлены." -ForegroundColor Green

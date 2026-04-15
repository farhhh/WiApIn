Write-Host "--- Глубокая очистка системы ---" -ForegroundColor Cyan

# 1. Очистка временных файлов пользователя
Write-Host "Очистка Temp пользователя..." -ForegroundColor Yellow
Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue

# 2. Очистка системного Temp
Write-Host "Очистка системного Temp..." -ForegroundColor Yellow
Remove-Item -Path "C:\Windows\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue

# 3. Очистка кэша загрузок обновлений Windows (SoftwareDistribution)
# Это часто весит по 2-5 ГБ
Write-Host "Очистка кэша обновлений Windows..." -ForegroundColor Yellow
Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Windows\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
Start-Service -Name wuauserv -ErrorAction SilentlyContinue

# 4. Очистка Prefetch (ускоряет систему, если накопилось много старого софта)
Write-Host "Очистка Prefetch..." -ForegroundColor Yellow
Remove-Item -Path "C:\Windows\Prefetch\*" -Recurse -Force -ErrorAction SilentlyContinue

# 5. Очистка корзины для всех дисков
Write-Host "Очистка корзины..." -ForegroundColor Yellow
Clear-RecycleBin -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "`n[OK] Система очищена!" -ForegroundColor Green

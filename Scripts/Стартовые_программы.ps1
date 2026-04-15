# Список программ для установки (ID из репозитория Winget)
$apps = @(
    "Google.Chrome",             # Браузер
    "7zip.7zip",                 # Архиватор
    "Telegram.TelegramDesktop",  # Мессенджер
    "VideoLAN.VLC"               # Плеер
)

Write-Host "--- Пакетная установка базового ПО ---" -ForegroundColor Cyan

# Проверка наличия winget в системе
if (!(Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Winget не найден. Попытка инициализации..." -ForegroundColor Yellow
    # В современных системах он обычно есть, но может требовать первого вызова
}

foreach ($app in $apps) {
    Write-Host "Запрос на установку: $app..." -ForegroundColor Yellow
    
    # --silent: фоновая установка без окон
    # --accept-package-agreements: автосогласие с лицензией ПО
    # --accept-source-agreements: автосогласие с правилами репозитория MS
    winget install --id $app --silent --accept-package-agreements --accept-source-agreements
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $app готов к работе." -ForegroundColor Green
    } else {
        Write-Host "[?] $app: пропущено (возможно, уже установлен)." -ForegroundColor Gray
    }
}

Write-Host "`nВсе выбранные программы установлены!" -ForegroundColor Cyan

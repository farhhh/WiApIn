$registryPath = "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
Write-Host "Настройка лимитов видеокарты для рендеринга..." -ForegroundColor Cyan

# Устанавливаем задержку в 60 секунд (по умолчанию 2)
New-ItemProperty -Path $registryPath -Name "TdrDelay" -Value 60 -PropertyType DWORD -Force
New-ItemProperty -Path $registryPath -Name "TdrDdiDelay" -Value 60 -PropertyType DWORD -Force

Write-Host "[OK] Теперь тяжелые рендеры не будут выбивать драйвер!" -ForegroundColor Green

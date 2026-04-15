Write-Host "WiApIn Test: Скрипт успешно запущен!"
$path = "$env:USERPROFILE\Desktop\WiApIn_Test.log"
"Тест пройден $(Get-Date)" | Out-File -FilePath $path
exit 0

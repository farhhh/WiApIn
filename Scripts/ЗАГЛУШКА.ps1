Write-Host "WiApIn Test: Скрипт успешно запущен!"
$path = "$env:USERPROFILE\Desktop\dynamic_test_1_WiApIn_Test.log"
"Тест пройден $(Get-Date)" | Out-File -FilePath $path
exit 0

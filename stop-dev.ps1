Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like "*uvicorn app.main:app*"} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

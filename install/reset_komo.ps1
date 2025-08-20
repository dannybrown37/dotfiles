$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

komorebic stop
taskkill /f /im komorebi.exe
taskkill /f /im whkd.exe
taskkill /f /im komorebi-bar.exe
komorebic start --whkd --bar

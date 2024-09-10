param (
    [string]$Command
)
Start-Process powershell -ArgumentList $Command -Verb runAs

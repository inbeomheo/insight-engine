Set-Location -LiteralPath (Join-Path $PSScriptRoot '..\..\..\frontend')
node node_modules\next\dist\bin\next dev --hostname 127.0.0.1 --port 3000

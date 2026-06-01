param(
  [string]$Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$SkillServer = "C:\Users\qlqla\.codex\skills\webapp-testing\scripts\with_server.py"

function Stop-AutoQaProcesses {
  $targets = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and (
      (($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and ($_.CommandLine -like '*tests\e2e\autoqa\serve_chatmock.py*' -or $_.CommandLine -like '*\.venv\Scripts\python.exe  app.py*' -or $_.CommandLine -like '*\.venv\Scripts\python.exe app.py*')) -or
      (($_.Name -eq 'node.exe') -and ($_.CommandLine -like '*insight-engine\frontend\node_modules\next*' -or $_.CommandLine -like '*insight-engine\frontend\.next*' -or $_.CommandLine -like '*npm-cli.js*run dev --prefix frontend*')) -or
      (($_.Name -eq 'powershell.exe') -and $_.CommandLine -like '*serve_frontend.ps1*')
    )
  }
  foreach ($p in $targets) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
}

$env:PYTHONIOENCODING = 'utf-8'
$env:CHATMOCK_BASE_URL = 'http://127.0.0.1:8000/v1'
$env:CHATMOCK_API_KEY = 'dummy'
$env:CHATMOCK_DEBUG_MODEL = 'gpt-5.5'
$env:DEFAULT_MODEL = 'chatmock/gpt-5.5'
$env:SUPABASE_URL = ''
$env:SUPABASE_ANON_KEY = ''
$env:SUPABASE_SERVICE_ROLE_KEY = ''
$env:OPENAI_API_KEY = ''
$env:ANTHROPIC_API_KEY = ''
$env:GEMINI_API_KEY = ''
$env:DEEPSEEK_API_KEY = ''
$env:OPENROUTER_API_KEY = ''
$env:OLLAMA_BASE_URL = ''
$env:CORS_ORIGINS = 'http://localhost:3000,http://127.0.0.1:3000'
$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:5001'
$env:QA_FRONTEND_URL = 'http://127.0.0.1:3000'
$env:QA_BACKEND_URL = 'http://127.0.0.1:5001'

Stop-AutoQaProcesses
try {
  & $Python $SkillServer --timeout 180 `
    --server "$Python tests\e2e\autoqa\serve_chatmock.py" --port 8000 `
    --server "$Python app.py" --port 5001 `
    --server "powershell -NoProfile -ExecutionPolicy Bypass -File tests\e2e\autoqa\serve_frontend.ps1" --port 3000 `
    -- $Python tests\e2e\autoqa\run_autoqa.py
  exit $LASTEXITCODE
}
finally {
  Stop-AutoQaProcesses
}

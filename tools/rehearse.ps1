$ErrorActionPreference = "Stop"
Start-Transcript -Path "rehearsal-$(Get-Date -Format 'HHmmss').log"
function Step($cmd) {
    Write-Host "`n>>> $cmd" -ForegroundColor Cyan
    Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) { throw "FAILED: $cmd" }
}
try {
    Step 'docker compose down -v'
    Step 'docker compose up -d --build --wait'
    Step 'docker compose exec -T api python -m scripts.seed'
    Step 'docker compose exec -T api python -m scripts.verify_seed'
    Write-Host "`n>>> NULL-out" -ForegroundColor Cyan
    @"
ALTER TABLE users DISABLE TRIGGER trg_users_dual_write;
UPDATE users SET first_name = NULL, last_name = NULL;
ALTER TABLE users ENABLE TRIGGER trg_users_dual_write;
"@ | docker compose exec -T postgres sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB'
    if ($LASTEXITCODE -ne 0) { throw "FAILED: NULL-out" }
    Step 'docker compose exec -T api python -m scripts.demo_cp2'
}
finally { Stop-Transcript }

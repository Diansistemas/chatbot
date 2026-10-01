# Ejecuta los tests de la aplicacion.
#   Uso:  .\pruebas\ejecutar_tests.ps1            (ambas suites)
#         .\pruebas\ejecutar_tests.ps1 -SoloUnit   (solo suite Django)
#         .\pruebas\ejecutar_tests.ps1 -SoloFunc   (solo test funcional; necesita Ollama)
param(
    [switch]$SoloUnit,
    [switch]$SoloFunc
)
$ErrorActionPreference = "Continue"
$raiz = Split-Path $PSScriptRoot -Parent
Push-Location $raiz
try {
    . .\.venv\Scripts\Activate.ps1

    if (-not $SoloFunc) {
        Write-Host "`n=== SUITE DJANGO (manage.py test) ===" -ForegroundColor Cyan
        python manage.py test
        $unit = $LASTEXITCODE
    } else { $unit = 0 }

    if (-not $SoloUnit) {
        Write-Host "`n=== TEST FUNCIONAL (HTTP + NLP + LLM + cierre/email) ===" -ForegroundColor Cyan
        Write-Host "(requiere Ollama en localhost:11434; ~90-120 s)"
        python pruebas\funcional\test_funcional.py
        $func = $LASTEXITCODE
    } else { $func = 0 }

    Write-Host "`n=== RESUMEN ===" -ForegroundColor Cyan
    Write-Host "suite Django : $(if ($unit -eq 0) {'OK'} else {'FALLOS (exit ' + $unit + ')'})"
    Write-Host "test funcional: $(if ($func -eq 0) {'OK'} else {'FALLOS (exit ' + $func + ')'})"
    exit ([Math]::Max($unit, $func))
}
finally {
    Pop-Location
}

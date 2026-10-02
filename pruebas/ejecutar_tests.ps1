# Ejecuta los tests de la aplicacion.
#   Uso:  .\pruebas\ejecutar_tests.ps1            (ambas suites)
#         .\pruebas\ejecutar_tests.ps1 -SoloUnit   (solo suite Django)
#         .\pruebas\ejecutar_tests.ps1 -SoloFunc   (solo test funcional; necesita Ollama)
#
#   Nota: en Windows con politica de ejecucion restringida (por defecto),
#   lanzarlo como:
#         powershell -ExecutionPolicy Bypass -File .\pruebas\ejecutar_tests.ps1
param(
    [switch]$SoloUnit,
    [switch]$SoloFunc
)
$ErrorActionPreference = "Continue"
$raiz = Split-Path $PSScriptRoot -Parent
Push-Location $raiz
try {
    # El venv puede llamarse `venv` (instaladores) o `.venv`. Si no existe,
    # se usa el python del PATH: el script sigue siendo util en un contenedor.
    $venv = @('venv', '.venv') | Where-Object { Test-Path (Join-Path $raiz "$_\Scripts\Activate.ps1") } | Select-Object -First 1
    if ($venv) {
        Write-Host "(venv: $venv)" -ForegroundColor DarkGray
        . (Join-Path $raiz "$venv\Scripts\Activate.ps1")
    } else {
        Write-Host "(sin venv local; usando python del PATH)" -ForegroundColor DarkYellow
    }

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
    } else { $func = -1 }

    Write-Host "`n=== RESUMEN ===" -ForegroundColor Cyan
    Write-Host "suite Django : $(if ($SoloFunc) {'omitido (-SoloFunc)'} elseif ($unit -eq 0) {'OK'} else {'FALLOS (exit ' + $unit + ')'})"
    Write-Host "test funcional: $(if ($SoloUnit) {'omitido (-SoloUnit)'} elseif ($func -eq 0) {'OK'} else {'FALLOS (exit ' + $func + ')'})"
    $codigos = @($unit, $func) | Where-Object { $_ -ge 0 }
    if ($codigos.Count -eq 0) { exit 0 }
    exit ($codigos | Measure-Object -Maximum).Maximum
}
finally {
    Pop-Location
}

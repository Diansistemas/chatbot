# Bateria de evaluacion del modelo NLP tras un reentrenamiento.
#   Uso:  .\pruebas\evaluacion\evaluar_todo.ps1
# Requisitos: modelo activo en entrenamiento\spacy\modelo\model-best y
# backups en $env:TEMP\opencode\backup_premerge (eval_rondas los usa para comparar).
param(
    [string]$LogEntrenamiento = ""   # log de `spacy train` para analizar curvas
)
$ErrorActionPreference = "Continue"
$raiz = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Push-Location $raiz
try {
    . .\.venv\Scripts\Activate.ps1

    Write-Host "`n=== 1/4 COMPARATIVA DE RONDAS (mismo dev) ===" -ForegroundColor Cyan
    python pruebas\evaluacion\eval_rondas.py

    Write-Host "`n=== 2/4 VERIFICACION DIRIGIDA (familias + regresiones) ===" -ForegroundColor Cyan
    python pruebas\evaluacion\verifica_ronda8.py

    Write-Host "`n=== 3/4 MATRIZ DE CONFUSION ===" -ForegroundColor Cyan
    python pruebas\evaluacion\confusion.py

    Write-Host "`n=== 4/4 SONDEO OOD (cerrar indebido) ===" -ForegroundColor Cyan
    python pruebas\evaluacion\smoke_sondeo.py

    if ($LogEntrenamiento -and (Test-Path $LogEntrenamiento)) {
        Write-Host "`n=== CURVAS DE ENTRENAMIENTO ===" -ForegroundColor Cyan
        python pruebas\evaluacion\analizar_entrenamiento.py $LogEntrenamiento
    }
}
finally {
    Pop-Location
}

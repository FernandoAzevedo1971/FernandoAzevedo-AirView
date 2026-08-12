# criar_atalho.ps1 — Cria o atalho "Painel CPAP" na área de trabalho,
# apontando para abrir_painel.bat. Chamado por criar_atalho_area_trabalho.bat
# (não precisa rodar este .ps1 diretamente).

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$alvo = Join-Path $scriptDir "abrir_painel.bat"
$desktop = [Environment]::GetFolderPath("Desktop")
$atalhoPath = Join-Path $desktop "Painel CPAP.lnk"

if (-not (Test-Path $alvo)) {
    Write-Host "ERRO: nao encontrei $alvo" -ForegroundColor Red
    Write-Host "Rode este script de dentro da pasta FernandoAzevedo-AirView."
    exit 1
}

$ws = New-Object -ComObject WScript.Shell
$atalho = $ws.CreateShortcut($atalhoPath)
$atalho.TargetPath = $alvo
$atalho.WorkingDirectory = $scriptDir
$atalho.Description = "Abrir painel MONITORAMENTO_CPAP_FAPS"
$atalho.Save()

Write-Host ""
Write-Host "Atalho 'Painel CPAP' criado na area de trabalho!" -ForegroundColor Green
Write-Host "Local: $atalhoPath"

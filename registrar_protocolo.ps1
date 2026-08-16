# registrar_protocolo.ps1 — Registra o protocolo cpapsync:// no Windows,
# apontando para executar_sync.bat desta pasta. Depois disso, um link como
# <a href="cpapsync://sincronizar"> no painel Next.js abre e roda a
# sincronização com o AirView automaticamente.
#
# Mexe só no registro do USUÁRIO ATUAL (HKCU) — não precisa ser Administrador.
# Chamado por registrar_protocolo.bat (não precisa rodar este .ps1 direto).

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$alvo = Join-Path $scriptDir "executar_sync.bat"

if (-not (Test-Path $alvo)) {
    Write-Host "ERRO: nao encontrei $alvo" -ForegroundColor Red
    Write-Host "Rode este script de dentro da pasta FernandoAzevedo-AirView."
    exit 1
}

$protocolKey = "HKCU:\Software\Classes\cpapsync"
$commandKey = "$protocolKey\shell\open\command"

New-Item -Path $protocolKey -Force | Out-Null
Set-ItemProperty -Path $protocolKey -Name "(Default)" -Value "URL:CPAP Sync Protocol"
Set-ItemProperty -Path $protocolKey -Name "URL Protocol" -Value ""

New-Item -Path $commandKey -Force | Out-Null
$comando = "`"$alvo`" `"%1`""
Set-ItemProperty -Path $commandKey -Name "(Default)" -Value $comando

Write-Host ""
Write-Host "Protocolo cpapsync:// registrado com sucesso!" -ForegroundColor Green
Write-Host "Alvo: $alvo"
Write-Host ""
Write-Host "Teste agora: pressione Win+R, cole  cpapsync:sincronizar  e Enter."
Write-Host "O Windows/navegador deve perguntar se pode abrir esse link com este"
Write-Host "programa -- confirme, e a sincronizacao deve iniciar numa nova janela."

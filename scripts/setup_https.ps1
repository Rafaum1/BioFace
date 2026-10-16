$ErrorActionPreference = 'Stop'

if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
    throw 'mkcert não foi encontrado. Instale-o com: winget install --id FiloSottile.mkcert --exact. Depois feche e abra o PowerShell e execute este script novamente.'
}

$probe = [System.Net.Sockets.UdpClient]::new()
try {
    $probe.Connect('192.0.2.1', 80)
    $lanIp = $probe.Client.LocalEndPoint.Address.IPAddressToString
}
finally {
    $probe.Dispose()
}

if (-not $lanIp -or $lanIp.StartsWith('127.')) {
    throw 'Não consegui detectar o IPv4 da rede. Conecte o computador ao Wi-Fi e tente novamente.'
}

$projectDir = Split-Path -Parent $PSScriptRoot
$certDir = Join-Path $projectDir 'certs'
New-Item -ItemType Directory -Path $certDir -Force | Out-Null
$certFile = Join-Path $certDir 'local-cert.pem'
$keyFile = Join-Path $certDir 'local-key.pem'

mkcert -install
if ($LASTEXITCODE -ne 0) { throw 'O mkcert não conseguiu instalar a autoridade certificadora local.' }

mkcert -cert-file $certFile -key-file $keyFile localhost 127.0.0.1 ::1 $lanIp
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível gerar o certificado HTTPS.' }

$caRoot = (mkcert -CAROOT | Select-Object -Last 1).Trim()
$rootCertificate = Join-Path $certDir 'rootCA.pem'
Copy-Item -LiteralPath (Join-Path $caRoot 'rootCA.pem') -Destination $rootCertificate -Force

Write-Host ''
Write-Host 'HTTPS configurado para este computador.' -ForegroundColor Green
Write-Host "Endereço local: https://localhost:5000"
Write-Host "Endereço na rede: https://${lanIp}:5000"
Write-Host "Para outro PC confiar no certificado, copie somente $rootCertificate para ele e execute:"
Write-Host 'certutil -addstore -user Root .\rootCA.pem'
Write-Host 'Não compartilhe o arquivo rootCA-key.pem.' -ForegroundColor Yellow

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$name = 'jdk25-jdtls-1.63.0-windows-x64.zip'
$parts = @('jdk25-jdtls-1.63.0-windows-x64.zip.001','jdk25-jdtls-1.63.0-windows-x64.zip.002','jdk25-jdtls-1.63.0-windows-x64.zip.003','jdk25-jdtls-1.63.0-windows-x64.zip.004','jdk25-jdtls-1.63.0-windows-x64.zip.005','jdk25-jdtls-1.63.0-windows-x64.zip.006','jdk25-jdtls-1.63.0-windows-x64.zip.007','jdk25-jdtls-1.63.0-windows-x64.zip.008')
$target = [IO.File]::Create((Join-Path $PSScriptRoot $name))
try {
  foreach ($part in $parts) {
    $source = [IO.File]::OpenRead((Join-Path $PSScriptRoot $part))
    try { $source.CopyTo($target) } finally { $source.Dispose() }
  }
} finally { $target.Dispose() }
if ((Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash.ToLowerInvariant() -ne '2a64b61c8d98c54c42ec02b6d4559b17aac2d4975209d3aa154f98fbd6b36d40') { throw 'ZIP checksum mismatch; download every part again.' }
Write-Host "Created and verified $name"

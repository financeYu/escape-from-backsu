[CmdletBinding()]
param(
    [switch]$Quiet
)

$utf8NoBom = New-Object System.Text.UTF8Encoding $false

[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$global:OutputEncoding = $utf8NoBom

if (-not $global:PSDefaultParameterValues) {
    $global:PSDefaultParameterValues = @{}
}

$defaultEncoding = if ($PSVersionTable.PSVersion.Major -ge 6) { "utf8NoBOM" } else { "utf8" }
$encodingCommands = @(
    "Add-Content",
    "Export-Csv",
    "Get-Content",
    "Import-Csv",
    "Out-File",
    "Set-Content",
    "Start-Transcript"
)

foreach ($commandName in $encodingCommands) {
    $global:PSDefaultParameterValues[("{0}:Encoding" -f $commandName)] = $defaultEncoding
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LESSCHARSET = "utf-8"

$chcp = Get-Command chcp.com -ErrorAction SilentlyContinue
if ($chcp) {
    & $chcp.Source 65001 | Out-Null
}

if (-not $Quiet) {
    Write-Host "PowerShell UTF-8 encoding is enabled for this session."
}

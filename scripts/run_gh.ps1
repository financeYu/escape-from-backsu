$ErrorActionPreference = "Stop"

$GhArgs = @($args)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

if ($GhArgs -and $GhArgs.Count -gt 0 -and $GhArgs[0] -eq "--") {
    if ($GhArgs.Count -eq 1) {
        $GhArgs = @()
    } else {
        $GhArgs = $GhArgs[1..($GhArgs.Count - 1)]
    }
}

function Add-CandidatePath {
    param(
        [System.Collections.Generic.List[string]]$Candidates,
        [string]$Path
    )
    if ($Path -and (Test-Path -LiteralPath $Path -PathType Leaf) -and -not $Candidates.Contains($Path)) {
        [void]$Candidates.Add($Path)
    }
}

function Get-EnvValue {
    param([string]$Name)
    return [System.Environment]::GetEnvironmentVariable($Name, "Process")
}

function Get-MergedPathValue {
    param([System.Collections.IDictionary]$Environment)

    $seen = New-Object "System.Collections.Generic.HashSet[string]" ([System.StringComparer]::OrdinalIgnoreCase)
    $items = New-Object "System.Collections.Generic.List[string]"

    foreach ($key in $Environment.Keys) {
        $name = [string]$key
        if ($name -ieq "PATH") {
            $value = [string]$Environment[$key]
            foreach ($part in ($value -split ";")) {
                $trimmed = $part.Trim()
                if ($trimmed.Length -gt 0 -and $seen.Add($trimmed)) {
                    [void]$items.Add($trimmed)
                }
            }
        }
    }

    return ($items -join ";")
}

function Normalize-CurrentProcessEnvironment {
    $sourceEnv = [System.Environment]::GetEnvironmentVariables("Process")

    $pathValue = Get-MergedPathValue $sourceEnv
    foreach ($key in $sourceEnv.Keys) {
        $name = [string]$key
        if ($name -ieq "PATH") {
            [System.Environment]::SetEnvironmentVariable($name, $null, "Process")
        }
    }
    if ($pathValue.Length -gt 0) {
        [System.Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
    }

    $groups = @{}
    $sourceEnv = [System.Environment]::GetEnvironmentVariables("Process")
    foreach ($key in $sourceEnv.Keys) {
        $name = [string]$key
        if ([string]::IsNullOrWhiteSpace($name) -or $name -ieq "PATH") {
            continue
        }

        $canonical = $name.ToUpperInvariant()
        if (-not $groups.ContainsKey($canonical)) {
            $groups[$canonical] = New-Object "System.Collections.Generic.List[string]"
        }
        [void]$groups[$canonical].Add($name)
    }

    foreach ($canonical in $groups.Keys) {
        $names = $groups[$canonical]
        if ($names.Count -le 1) {
            continue
        }

        $selectedName = $names[0]
        $selectedValue = [string][System.Environment]::GetEnvironmentVariable($selectedName, "Process")
        foreach ($name in $names) {
            $value = [string][System.Environment]::GetEnvironmentVariable($name, "Process")
            if ($selectedValue.Length -eq 0 -and $value.Length -gt 0) {
                $selectedName = $name
                $selectedValue = $value
            }
        }

        foreach ($name in $names) {
            [System.Environment]::SetEnvironmentVariable($name, $null, "Process")
        }
        [System.Environment]::SetEnvironmentVariable($selectedName, $selectedValue, "Process")
    }

    [System.Environment]::SetEnvironmentVariable("GH_PROMPT_DISABLED", "1", "Process")
    [System.Environment]::SetEnvironmentVariable("GH_NO_UPDATE_NOTIFIER", "1", "Process")
    if (-not [System.Environment]::GetEnvironmentVariable("NO_COLOR", "Process")) {
        [System.Environment]::SetEnvironmentVariable("NO_COLOR", "1", "Process")
    }
}

function Set-CleanProcessEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.ProcessStartInfo]$ProcessInfo
    )

    Normalize-CurrentProcessEnvironment

    $sourceEnv = [System.Environment]::GetEnvironmentVariables("Process")
    $chosen = @{}

    foreach ($key in $sourceEnv.Keys) {
        $name = [string]$key
        if ([string]::IsNullOrWhiteSpace($name) -or $name -ieq "PATH") {
            continue
        }

        $canonical = $name.ToUpperInvariant()
        if (-not $chosen.ContainsKey($canonical)) {
            $chosen[$canonical] = @{
                Name = $name
                Value = [string]$sourceEnv[$key]
            }
            continue
        }

        $current = $chosen[$canonical]
        $currentValue = [string]$current.Value
        $newValue = [string]$sourceEnv[$key]
        if ($currentValue.Length -eq 0 -and $newValue.Length -gt 0) {
            $chosen[$canonical] = @{
                Name = $name
                Value = $newValue
            }
        }
    }

    $targetEnv = $ProcessInfo.EnvironmentVariables
    if ($null -eq $targetEnv) {
        throw "ProcessStartInfo environment could not be initialized after project environment normalization."
    }
    $targetEnv.Clear()

    $pathValue = Get-MergedPathValue $sourceEnv
    if ($pathValue.Length -gt 0) {
        $targetEnv["Path"] = $pathValue
    }

    foreach ($entry in $chosen.Values) {
        $targetEnv[[string]$entry.Name] = [string]$entry.Value
    }

    $targetEnv["GH_PROMPT_DISABLED"] = "1"
    $targetEnv["GH_NO_UPDATE_NOTIFIER"] = "1"
    if (-not $targetEnv.ContainsKey("NO_COLOR")) {
        $targetEnv["NO_COLOR"] = "1"
    }
}

function ConvertTo-ProcessArgument {
    param([string]$Argument)
    if ($null -eq $Argument) {
        return '""'
    }
    if ($Argument -notmatch '[\s"]') {
        return $Argument
    }
    return '"' + ($Argument -replace '"', '\"') + '"'
}

function Redact-GhText {
    param([string]$Text)
    $redacted = $Text
    $redacted = $redacted -replace "(?i)(GH_TOKEN|GITHUB_TOKEN|GH_ENTERPRISE_TOKEN|GITHUB_ENTERPRISE_TOKEN)=\S+", '$1=<redacted>'
    $redacted = $redacted -replace "(?i)(token|authorization):\s*\S+", '$1: <redacted>'
    return $redacted
}

$ghCandidates = New-Object "System.Collections.Generic.List[string]"
Add-CandidatePath $ghCandidates (Get-EnvValue "PROJECT_GH")
Add-CandidatePath $ghCandidates (Join-Path $repoRoot "tools\gh\gh.exe")
Add-CandidatePath $ghCandidates (Join-Path $repoRoot "tools\gh\bin\gh.exe")
Add-CandidatePath $ghCandidates "C:\Program Files\GitHub CLI\gh.exe"
$localAppData = Get-EnvValue "LOCALAPPDATA"
if ($localAppData) {
    Add-CandidatePath $ghCandidates (Join-Path $localAppData "Programs\GitHub CLI\gh.exe")
}

if ($ghCandidates.Count -eq 0) {
    Write-Output "BLOCKED_GH_ENV: gh executable was not found. Install GitHub CLI or set PROJECT_GH to the full gh.exe path before using this wrapper."
    exit 127
}

$startFailures = @()

foreach ($ghPath in $ghCandidates) {
    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = $ghPath
    $processInfo.Arguments = (($GhArgs | ForEach-Object { ConvertTo-ProcessArgument $_ }) -join " ")
    $processInfo.WorkingDirectory = $repoRoot
    $processInfo.UseShellExecute = $false
    $processInfo.RedirectStandardOutput = $true
    $processInfo.RedirectStandardError = $true
    Set-CleanProcessEnvironment -ProcessInfo $processInfo

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $processInfo

    try {
        [void]$process.Start()
        $stdoutText = $process.StandardOutput.ReadToEnd()
        $stderrText = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
    } catch {
        $startFailures += "gh_path: $ghPath; blocked_error: $($_.Exception.Message)"
        continue
    }

    $text = (($stdoutText + $stderrText) -replace "`0", "")
    if ($text.Trim().Length -gt 0) {
        Write-Output (Redact-GhText $text.TrimEnd())
    }

    exit $process.ExitCode
}

Write-Output "BLOCKED_GH_ENV: all gh candidates failed to start with normalized project environment."
foreach ($failure in $startFailures) {
    Write-Output (Redact-GhText $failure)
}
exit 125

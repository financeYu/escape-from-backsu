param(
    [string]$ShortcutName = "Master MVP GUI",
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$shortcutLeaf = [System.IO.Path]::GetFileName($ShortcutName)
if ([string]::IsNullOrWhiteSpace($shortcutLeaf) -or $ShortcutName -ne $shortcutLeaf) {
    throw "ShortcutName must be a file name only, without path separators."
}
if ($shortcutLeaf.IndexOfAny([System.IO.Path]::GetInvalidFileNameChars()) -ge 0) {
    throw "ShortcutName contains invalid file name characters."
}
if ($shortcutLeaf.EndsWith(".lnk", [System.StringComparison]::OrdinalIgnoreCase)) {
    $shortcutFileName = $shortcutLeaf
} else {
    $shortcutFileName = "$shortcutLeaf.lnk"
}

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $pythonCommand = Get-Command python -ErrorAction Stop
    $pythonwPath = Join-Path (Split-Path -Parent $pythonCommand.Source) "pythonw.exe"
    if (Test-Path $pythonwPath) {
        $PythonPath = $pythonwPath
    } else {
        $PythonPath = $pythonCommand.Source
    }
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop $shortcutFileName

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $PythonPath
$shortcut.Arguments = "-m gui_mvp"
$shortcut.WorkingDirectory = $repoRoot.Path
$shortcut.Description = "Open Master MVP chart and backtest viewers"
$shortcut.Save()

Write-Output $shortcutPath

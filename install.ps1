$ErrorActionPreference = "Stop"

$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
& $python -c "import sys; raise SystemExit('YouRich requires Python 3.11 or newer.') if sys.version_info < (3, 11) else None"

$installed = $false
$skillSource = Join-Path $PWD "skill\yourich"

if ((Get-Command claude -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $HOME ".claude"))) {
    $claudeSkills = Join-Path $HOME ".claude\skills"
    $claudeTarget = Join-Path $claudeSkills "yourich"
    New-Item -ItemType Directory -Force -Path $claudeSkills | Out-Null
    Remove-Item -Recurse -Force -LiteralPath $claudeTarget -ErrorAction SilentlyContinue
    Copy-Item -Recurse -LiteralPath $skillSource -Destination $claudeTarget
    $installed = $true
    Write-Host "Installed YouRich skill for Claude Code."
}

if ((Get-Command codex -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $HOME ".codex"))) {
    $codexSkills = Join-Path $HOME ".codex\skills"
    $codexTarget = Join-Path $codexSkills "yourich"
    New-Item -ItemType Directory -Force -Path $codexSkills | Out-Null
    Remove-Item -Recurse -Force -LiteralPath $codexTarget -ErrorAction SilentlyContinue
    Copy-Item -Recurse -LiteralPath $skillSource -Destination $codexTarget
    $installed = $true
    Write-Host "Installed YouRich skill for Codex."
}

if (-not $installed) {
    Write-Host "No Claude Code or Codex user directory detected. Skill source remains at skill\yourich."
}

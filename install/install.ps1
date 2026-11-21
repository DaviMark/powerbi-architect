<#
.SYNOPSIS
  Install the powerbi-architect skill into a repository (or globally) for every major AI agent.
.EXAMPLE
  .\install\install.ps1 -Target C:\repos\my-bi-repo
  .\install\install.ps1 -Global
  .\install\install.ps1 -Target . -Force
  .\install\install.ps1 -Target . -NoGraph
  .\install\install.ps1 -Target . -Status     # installed version vs this copy, changes nothing
  .\install\install.ps1 -Target . -Update     # replace older installations (git pull this repo first)
.NOTES
  Nothing is downloaded. After copying, and only for a repository install, the installer runs the
  skill's own offline script (scripts\pbi_graph.py, Python stdlib) to build powerbi-graph\, add a short
  section to AGENTS.md/CLAUDE.md and add refresh hooks. -NoGraph skips that; -NoHooks skips only the hooks.
#>
param(
  [string]$Target = ".",
  [switch]$Global,
  [switch]$Force,
  [switch]$NoGraph,
  [switch]$NoHooks,
  [switch]$Status,
  [switch]$Update
)
$ErrorActionPreference = "Stop"
$Src = Join-Path (Split-Path -Parent $PSScriptRoot) "skills\powerbi-architect"
if (-not (Test-Path (Join-Path $Src "SKILL.md"))) { throw "SKILL.md not found in $Src" }
function Get-SkillVersion([string]$Dir) {
  $f = Join-Path $Dir "SKILL.md"
  if (-not (Test-Path $f)) { return "" }
  $m = Select-String -Path $f -Pattern 'version:\s*"([^"]+)"' | Select-Object -First 1
  if ($m) { return $m.Matches[0].Groups[1].Value } else { return "" }
}
$Version = Get-SkillVersion $Src

if ($Global) {
  $Dests = @("$HOME\.claude\skills", "$HOME\.copilot\skills", "$HOME\.codex\skills")
} else {
  $T = (Resolve-Path $Target).Path
  $Dests = @("$T\.claude\skills", "$T\.github\skills", "$T\.agents\skills")
}

if ($Status) {
  Write-Host "This copy: powerbi-architect $Version ($Src)"
  foreach ($d in $Dests) {
    $dest = Join-Path $d "powerbi-architect"
    if (Test-Path $dest) {
      $v = Get-SkillVersion $dest
      if ($v -eq $Version) { Write-Host "  ${dest}: $v (up to date)" } else { Write-Host "  ${dest}: $v (update available: $Version)" }
    } else { Write-Host "  ${dest}: not installed" }
  }
  exit 0
}

$Changed = $false
foreach ($d in $Dests) {
  $dest = Join-Path $d "powerbi-architect"
  if ($Update) {
    if (-not (Test-Path $dest)) { Write-Host "• not installed, skipped: $dest"; continue }
    $old = Get-SkillVersion $dest
    if ($old -eq $Version -and -not $Force) { Write-Host "• up to date (${Version}): $dest"; continue }
    Remove-Item -Recurse -Force $dest
    Write-Host "  $old -> $Version"
  } elseif (Test-Path $dest) {
    if ($Force) { Remove-Item -Recurse -Force $dest } else { Write-Host "• exists, skipped: $dest (use -Force, or -Update)"; continue }
  }
  $Changed = $true
  New-Item -ItemType Directory -Force -Path $d | Out-Null
  Copy-Item -Recurse -Path $Src -Destination $dest
  $nm = Join-Path $dest "templates\pbiviz-bullet-kpi\node_modules"
  if (Test-Path $nm) { Remove-Item -Recurse -Force $nm }
  Write-Host "[ok] $dest"
}
if ($Update -and -not $Changed) { Write-Host "Nothing to update."; exit 0 }
if (-not $Global -and -not $NoGraph) {
  $Py = $null
  foreach ($c in @("python", "python3", "py")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike "*WindowsApps*") { $Py = $c; break }
  }
  if (-not $Py) {
    Write-Host "! Python 3.9+ not found - knowledge graph skipped. Later: python .claude\skills\powerbi-architect\scripts\pbi_graph.py install ."
  } else {
    Write-Host "`nBuilding the Power BI knowledge graph..."
    $extra = @(); if ($NoHooks) { $extra += "--no-hooks" }
    Push-Location $T
    try { & $Py ".claude\skills\powerbi-architect\scripts\pbi_graph.py" install . @extra } finally { Pop-Location }
  }
} elseif ($Global) {
  Write-Host "Global install: build a repository's graph with"
  Write-Host "  python $HOME\.claude\skills\powerbi-architect\scripts\pbi_graph.py install C:\path\to\repo"
}
Write-Host "`npowerbi-architect $Version installed. Ask your AI for any Power BI work — the skill loads automatically."

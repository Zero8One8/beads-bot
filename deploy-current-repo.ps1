param(
    [string]$Message = "Update current repo",
    [switch]$Railway,
    [string]$RailwayProject = ""
)

Set-Location -Path $PSScriptRoot
Write-Host "Repository path: $PWD"

# Git add / commit / push
git add .
try {
    git commit -m "$Message"
} catch {
    Write-Warning "No changes to commit or commit failed."
}
git push origin main

if ($Railway) {
    if (-not $RailwayProject) {
        Write-Error "Railway project name is required when using -Railway."
        exit 1
    }
    railway switch $RailwayProject
    railway up
}

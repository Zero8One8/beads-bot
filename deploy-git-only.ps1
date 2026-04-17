Set-Location -Path $PSScriptRoot
Write-Host "Repository path: $PWD"

git add .
try {
    git commit -m "Update code"
} catch {
    Write-Warning "No changes to commit."
}

git push origin main
Write-Host "Done."
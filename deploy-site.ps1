# ОТКРОЙ И ОТРЕДАКТИРУЙ ЭТИ ПЕРЕМЕННЫЕ ОДИН РАЗ
$SiteRepoPath = "C:\path\to\site-repo"
$SiteRailwayProject = "site-project-name"

Set-Location -Path $SiteRepoPath
Write-Host "Site repository path: $PWD"

git add .
try {
    git commit -m "Update site"
} catch {
    Write-Warning "No changes to commit or commit failed."
}
git push origin main

railway switch $SiteRailwayProject
railway up

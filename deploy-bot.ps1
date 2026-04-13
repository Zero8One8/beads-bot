# ОТКРОЙ И ОТРЕДАКТИРУЙ ЭТИ ПЕРЕМЕННЫЕ ОДИН РАЗ
$BotRepoPath = "C:\path\to\bot-repo"
$BotRailwayProject = "bot-project-name"

Set-Location -Path $BotRepoPath
Write-Host "Bot repository path: $PWD"

git add .
try {
    git commit -m "Update bot"
} catch {
    Write-Warning "No changes to commit or commit failed."
}
git push origin main

railway switch $BotRailwayProject
railway up
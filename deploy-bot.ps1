# ОТКРОЙ И ОТРЕДАКТИРУЙ ЭТИ ПЕРЕМЕННЫЕ ОДИН РАЗ
$BotRepoPath = "C:\path\to\bot-repo"
$BotRailwayProject = "bot-project-name"

$defaultPath = "C:\path\to\bot-repo"
if ($BotRepoPath -eq $defaultPath) {
    Write-Warning "BotRepoPath не настроен. Использую папку со скриптом: $PSScriptRoot"
    $BotRepoPath = $PSScriptRoot
}

if (-not (Test-Path $BotRepoPath)) {
    Write-Error "Не найден путь к репозиторию бота: $BotRepoPath. Измени переменную в скрипте или помести скрипт в корень бота."
    exit 1
}

Set-Location -Path $BotRepoPath
Write-Host "Bot repository path: $PWD"

git add .
try {
    git commit -m "Update bot"
} catch {
    Write-Warning "No changes to commit or commit failed."
}
git push origin main

function Run-RailwayCommand($args) {
    if (-not (Get-Command railway -ErrorAction SilentlyContinue)) {
        Write-Warning "Railway CLI не найден. Установи его или запускай deploy вручную."
        return
    }
    if ($args -match 'switch') {
        if ($BotRailwayProject -eq "bot-project-name") {
            Write-Warning "BotRailwayProject не установлен. Пропускаю switch."
            return
        }
    }
    Write-Host "railway $args"
    & railway $args
}

Run-RailwayCommand "switch $BotRailwayProject"
Run-RailwayCommand "up"
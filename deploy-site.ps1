# ОТКРОЙ И ОТРЕДАКТИРУЙ ЭТИ ПЕРЕМЕННЫЕ ОДИН РАЗ
$SiteRepoPath = "C:\path\to\site-repo"
$SiteRailwayProject = "site-project-name"

$defaultPath = "C:\path\to\site-repo"
if ($SiteRepoPath -eq $defaultPath) {
    Write-Warning "SiteRepoPath не настроен. Использую папку со скриптом: $PSScriptRoot"
    $SiteRepoPath = $PSScriptRoot
}

if (-not (Test-Path $SiteRepoPath)) {
    Write-Error "Не найден путь к репозиторию сайта: $SiteRepoPath. Измени переменную в скрипте или помести скрипт в корень сайта."
    exit 1
}

Set-Location -Path $SiteRepoPath
Write-Host "Site repository path: $PWD"

git add .
try {
    git commit -m "Update site"
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
        if ($SiteRailwayProject -eq "site-project-name") {
            Write-Warning "SiteRailwayProject не установлен. Пропускаю switch."
            return
        }
    }
    Write-Host "railway $args"
    & railway $args
}

Run-RailwayCommand "switch $SiteRailwayProject"
Run-RailwayCommand "up"

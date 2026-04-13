param(
    [string]$Message = "Update site and bot",
    [switch]$Railway
)

# Перейти в папку скрипта (репозиторий)
Set-Location -Path $PSScriptRoot

Write-Host "Repository path: $PWD"
Write-Host "Commit message: $Message"

# Проверка статуса
git status

# Добавить изменения
git add .

# Сделать коммит
try {
    git commit -m "$Message"
} catch {
    Write-Warning "Коммит не выполнен. Возможно, нет изменений для коммита."
}

# Запушить на GitHub
git push origin main

if ($Railway) {
    Write-Host "Запуск Railway deploy..."
    railway up
}

Write-Host "Готово. Если Railway настроен на автоматический деплой — сайт и бот обновятся после push."
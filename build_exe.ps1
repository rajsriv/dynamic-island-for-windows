# Build Script for Windows Dynamic Island
# Ensure you are in the project root and venv is active

$AppName = "DynamicIsland"
$MainScript = "main.py"

Write-Host "--- Starting Build Process for $AppName ---" -ForegroundColor Cyan

# Run PyInstaller with optimized flags
# --noconsole: Hide terminal window
# --onefile: Bundle into a single EXE
# --collect-all: Ensure complex packages like winsdk and qtawesome are fully included
# --hidden-import: Explicitly add winsdk if needed
.\venv\Scripts\pyinstaller --noconsole `
    --onefile `
    --name $AppName `
    --collect-all winsdk `
    --collect-all qtawesome `
    --hidden-import winsdk.windows.ui.notifications.management `
    $MainScript

Write-Host "--- Build Complete! Check the 'dist' folder ---" -ForegroundColor Green

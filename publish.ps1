$ErrorActionPreference = "Stop"

Write-Host "Starting deployment packaging..."

# Check if python is available
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    Write-Host "Using Python to create deployment package (Cross-platform compatible)..."
    python deploy.py
}
else {
    Write-Warning "Python not found in PATH. Falling back to PowerShell Compress-Archive (Windows paths only)."
    
    $zipFile = "deploy.zip"
    $itemsToZip = @(
        "app.py",
        "passenger_wsgi.py",
        "requirements.txt",
        "appsettings.json",
        "controllers",
        "db",
        "models",
        "routes",
        "static",
        "templates",
        "utils"
    )

    # Remove existing zip if it exists
    if (Test-Path $zipFile) {
        Remove-Item $zipFile -Force
        Write-Host "Removed existing $zipFile"
    }

    # Verify items exist
    $validItems = @()
    foreach ($item in $itemsToZip) {
        if (Test-Path $item) {
            $validItems += $item
        } else {
            Write-Warning "Item not found: $item"
        }
    }

    if ($validItems.Count -eq 0) {
        Write-Error "No valid items found to zip."
        exit 1
    }

    Write-Host "Compressing files to $zipFile..."
    Compress-Archive -Path $validItems -DestinationPath $zipFile -Force
    Write-Host "Done! File created: $zipFile"
}

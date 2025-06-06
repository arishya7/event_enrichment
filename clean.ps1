# This script removes temporary and output directories to clean the workspace.
# It checks if each directory exists before attempting to remove it.

# Define the list of directories to remove
$foldersToRemove = @(
    "RSS_temp",
    "events_output",
    "articles_output",
    "meta_database"
)

# Loop through each folder and remove it if it exists
foreach ($folder in $foldersToRemove) {
    if (Test-Path -Path $folder) {
        Write-Host "Removing directory: $folder"
        Remove-Item -Path $folder -Recurse -Force
    } else {
        Write-Host "Directory not found, skipping: $folder"
    }
}

Write-Host "Cleanup complete." 
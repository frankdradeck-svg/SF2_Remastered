$ffmpeg = "C:\Users\mastershred\ffmpeg.exe"

$sourceRoot = "C:\Users\mastershred\SF2_Remastered\sounds"
$outputRoot = "C:\Users\mastershred\SF2_Remastered\sounds\normalized\sounds"

# Loudness targets
$targetLUFS = -16
$truePeak = -2
$lra = 11

$extensions = @(".wav", ".mp3", ".ogg")

# Build the FFmpeg filter safely
$loudnormFilter = "loudnorm=I={0}:TP={1}:LRA={2}" -f $targetLUFS, $truePeak, $lra

# Only look at files directly inside the sounds folder.
# This prevents us from finding the files we already created
# inside normalized\.
$files = Get-ChildItem -Path $sourceRoot -File |
    Where-Object {
        $extensions -contains $_.Extension.ToLower() -and
        $_.Name -match "extraball"
    }

Write-Host ""
Write-Host "Found $($files.Count) matching files."
Write-Host ""
Write-Host "Target loudness: $targetLUFS LUFS"
Write-Host "True peak ceiling: $truePeak dB"
Write-Host "Output folder: $outputRoot"
Write-Host ""

if ($files.Count -eq 0) {
    Write-Host "No matching files found."
    exit
}

if (!(Test-Path $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
}

$count = 0
$errors = 0

foreach ($file in $files) {

    $outputFile = Join-Path $outputRoot $file.Name
    $count++

    Write-Host "[$count / $($files.Count)] $($file.Name)"

    switch ($file.Extension.ToLower()) {

        ".wav" {
            & $ffmpeg `
                -hide_banner `
                -loglevel error `
                -y `
                -i $file.FullName `
                -af $loudnormFilter `
                -c:a pcm_s16le `
                $outputFile
        }

        ".mp3" {
            & $ffmpeg `
                -hide_banner `
                -loglevel error `
                -y `
                -i $file.FullName `
                -af $loudnormFilter `
                -c:a libmp3lame `
                -q:a 2 `
                $outputFile
        }

        ".ogg" {
            & $ffmpeg `
                -hide_banner `
                -loglevel error `
                -y `
                -i $file.FullName `
                -af $loudnormFilter `
                -c:a libvorbis `
                -q:a 5 `
                $outputFile
        }
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR processing $($file.Name)" -ForegroundColor Red
        $errors++
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "Finished processing $count files."
Write-Host "Errors: $errors"
Write-Host ""
Write-Host "Normalized files are in:"
Write-Host $outputRoot
Write-Host "========================================"
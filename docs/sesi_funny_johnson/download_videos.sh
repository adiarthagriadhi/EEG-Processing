#!/bin/bash

# Google Drive file IDs
declare -A FILE_IDS
FILE_IDS[P08]="1EZI1g85MRr22r1WQsT44okRTEgfTNmct"
FILE_IDS[P09]="1nrEhTSZxFqQOfij9-4XfFUcEgfW4Q2Y6"
FILE_IDS[P11]="1oSM-WU-_mH09H7RSg2_NEmdMdDtwpAa_"
FILE_IDS[P30]="1RtJ6CqJKzRhcEEThzX9Bqz66jq-3BmgP"
FILE_IDS[P31]="18N5GhGhUVVq9dmP0uZxtzO0IsRLLLFGK"
FILE_IDS[P32]="129si_lLhjyhH74D63dU0IkkdYgsFZ1VI"

echo "Downloading video files from Google Drive..."
echo "============================================"

for pid in P08 P09 P11 P30 P31 P32; do
    file_id=${FILE_IDS[$pid]}
    output_dir="data/raw/$pid"
    
    echo -n "Downloading $pid... "
    
    # Download using gdown
    gdown "$file_id" -O "$output_dir/${pid}_video.webm" --quiet 2>/dev/null
    
    if [ -f "$output_dir/${pid}_video.webm" ]; then
        size=$(du -h "$output_dir/${pid}_video.webm" | cut -f1)
        echo "✓ OK ($size)"
    else
        echo "✗ FAILED"
    fi
done

echo "============================================"
echo "Download complete. Verifying files..."
ls -lh data/raw/*/P*_video.webm 2>/dev/null || echo "No videos found"

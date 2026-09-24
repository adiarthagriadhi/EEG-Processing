#!/bin/bash

# Try alternative gdown approach
FILE_IDS=(
    "1EZI1g85MRr22r1WQsT44okRTEgfTNmct:P08"
    "1nrEhTSZxFqQOfij9-4XfFUcEgfW4Q2Y6:P09"
    "1oSM-WU-_mH09H7RSg2_NEmdMdDtwpAa_:P11"
    "1RtJ6CqJKzRhcEEThzX9Bqz66jq-3BmgP:P30"
    "18N5GhGhUVVq9dmP0uZxtzO0IsRLLLFGK:P31"
    "129si_lLhjyhH74D63dU0IkkdYgsFZ1VI:P32"
)

echo "Attempting alternative download method..."
for pair in "${FILE_IDS[@]}"; do
    IFS=':' read -r file_id pid <<< "$pair"
    output_dir="data/raw/$pid"
    
    echo "Trying P$pid (ID: ${file_id:0:10}...)..."
    
    # Try with full URL
    url="https://drive.google.com/uc?id=$file_id&export=download"
    
    # Try curl with redirect
    curl -L "$url" -o "$output_dir/${pid}_video.webm" -C - --max-time 30 2>&1 | grep -E "(100|200|403|404|Authorization|cannot)" || true
done

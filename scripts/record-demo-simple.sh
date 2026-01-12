#!/bin/bash
# Simple script to record demo using browser automation
# Requires: playwright, ffmpeg

echo "Recording Agent Portal demo..."
python3 scripts/record-demo.py

echo "Demo recording complete!"
echo "Check webui/demo-new.gif"

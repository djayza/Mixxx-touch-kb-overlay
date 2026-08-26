#!/bin/bash
if pgrep -f "floating-touch-button.py" > /dev/null; then
    echo "Overlay running. Turning it OFF."
    pkill -f "floating-touch-button.py"
else
    echo "Overlay stopped. Turning it ON."
    python3 /home/mixxx/floating-touch-button.py &
fi

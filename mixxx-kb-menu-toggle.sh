#!/bin/bash
if pgrep -f "floating-touch-button.py" > /dev/null; then
    pkill -f "floating-touch-button.py"
else
    python3 /home/mixxx/Mixxx-touch-kb-overlay/floating-touch-button.py &
fi

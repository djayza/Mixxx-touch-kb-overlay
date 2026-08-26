#!/bin/bash
if pgrep -x "wvkbd-mobintl" > /dev/null; then
    pkill -x wvkbd-mobintl
else
    # Standard clean background execution structure
    QT_IM_MODULE=wayland wvkbd-mobintl -H 300 &
fi

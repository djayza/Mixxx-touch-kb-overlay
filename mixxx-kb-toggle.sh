#!/bin/bash
if pgrep -x "wvkbd-mobintl" > /dev/null; then
    pkill -x wvkbd-mobintl
else
    QT_IM_MODULE=wayland wvkbd-mobintl -H 300 &
fi

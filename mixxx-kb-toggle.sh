#!/bin/bash
if pgrep -x "wvkbd-mobintl" > /dev/null; then
    pkill -x wvkbd-mobintl
else
    # -L overlay instructs Labwc to forcefully keep wvkbd stacked on top of full-screen viewports
    QT_IM_MODULE=wayland wvkbd-mobintl -H 300 -L overlay &
fi

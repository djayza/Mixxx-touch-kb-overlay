#!/bin/bash
if pgrep -x "wvkbd-mobintl" > /dev/null; then
    pkill -x wvkbd-mobintl
else
    # -L forces it to use layer-shell to overlay full-screen exclusive apps
    # -bg sets background transparency blending rules
    QT_IM_MODULE=wayland wvkbd-mobintl -H 300 -L overlay -bg 000000aa &
fi

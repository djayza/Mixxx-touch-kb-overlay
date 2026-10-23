#!/bin/bash
# Installer for the Mixxx on-screen keyboard (Raspberry Pi OS, labwc)
set -e

DIR="$HOME/mixxx-osk"
mkdir -p "$DIR" "$HOME/.local/share/applications" "$HOME/.config/labwc"

echo "==> Installing packages"
sudo apt update
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
    gir1.2-gtklayershell-0.1 python3-evdev libnotify-bin

echo "==> Allowing key injection through /dev/uinput"
echo uinput | sudo tee /etc/modules-load.d/uinput.conf >/dev/null
sudo modprobe uinput || true
echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' \
    | sudo tee /etc/udev/rules.d/99-uinput.rules >/dev/null
sudo usermod -aG input "$USER"
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "==> Installing files into $DIR"
cp "$(dirname "$0")/mixxx-osk.py" "$DIR/mixxx-osk.py"
chmod +x "$DIR/mixxx-osk.py"

cat > "$HOME/.local/share/applications/mixxx-osk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Mixxx Touch Keyboard
Comment=Toggle the on-screen keyboard overlay for fullscreen Mixxx
Exec=$DIR/mixxx-osk.py
Icon=input-keyboard
Categories=Utility;Accessibility;
Terminal=false
EOF

# autostart under labwc (replace the old overlay entry if it exists)
AUTOSTART="$HOME/.config/labwc/autostart"
touch "$AUTOSTART"
sed -i '/mixxx-kb-menu-toggle.sh/d' "$AUTOSTART"
grep -q 'mixxx-osk.py' "$AUTOSTART" || echo "$DIR/mixxx-osk.py &" >> "$AUTOSTART"

echo
echo "Done. LOG OUT AND BACK IN (or reboot) so the 'input' group takes effect."

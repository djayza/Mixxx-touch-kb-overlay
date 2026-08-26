# Mixxx Wayland Touch Keyboard Overlay 🎛️🎹

An elegant, lightweight, native Wayland AssistiveTouch-style floating button designed for the **Raspberry Pi 5** running **Mixxx** inside a **Labwc** environment. It provides a persistent touch macro target layered permanently over full-screen DJ decks to easily trigger a virtual keyboard (`wvkbd`).

## ✨ Features
* **Zero-Stutter Native Overlay:** Anchored directly into the compositor layout workspace using `gtk-layer-shell` to sit securely on top of full-screen hardware-accelerated viewports.
* **1-Second Hold-to-Drag Activation:** Restrictive time gates ensure the button never moves by accident during energetic mixing. It flashes color when movement is unlocked.
* **Immediate Single-Tap Toggling:** Instantly updates your virtual keyboard mapping without stealing application layout focus.
* **3-Second Vanish Timer:** Press and hold statically for 3 seconds to cleanly hide the overlay completely.

## 🛠️ System Prerequisites
```bash
sudo apt update
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 wvkbd
```

## 🚀 Installation & Deployment
1. Clone this repository or copy the scripts to `/home/mixxx/`.
2. Ensure both files are executable:
   ```bash
   chmod +x floating-touch-button.py
   chmod +x mixxx-kb-toggle.sh
   ```
3. To automate the launcher, add the execution line to your Labwc environment autostart profile (~/.config/labwc/autostart):
   ```bash
   python3 /home/mixxx/mixxx-touch-kb-overlay/floating-touch-button.py &
   ```

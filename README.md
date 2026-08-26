# Mixxx Wayland Touch Keyboard Overlay 🎛️🎹

An elegant, native Wayland AssistiveTouch-style floating button designed for the **Raspberry Pi 5** running **Mixxx** inside a **Labwc** compositor environment. It provides a persistent, translucent gray touch macro target layered permanently over full-screen DJ decks to easily trigger a virtual keyboard layout (`wvkbd`) without losing focus or exiting full-screen mode.

---

## ✨ Features
* **Translucent Gray Skin:** Styled natively with Cairo graphics to blend seamlessly into Mixxx's premium dark theme without distracting from active track visualizer waveforms.
* **1-Second Hold-to-Drag Activation Lock:** Restrictive time gates ensure the button never moves by accident during quick crossfader or deck mixing manipulations. It flashes orange when movement is unlocked.
* **Full-Screen Layer Shell Overlay:** Configured via `wvkbd` Layer-Shell mode (`-L overlay`) to forcefully override Mixxx's full-screen graphics, unlocking library search box text entry with a single tap.
* **Accessories Menu Integration:** Seamlessly populates a custom shortcut into your Raspberry Pi OS **Start Menu -> Accessories** category list to quickly toggle the utility on or off.
* **3-Second Vanish Timer:** Press and hold statically inside the touch target area for 3 seconds to cleanly close the tool workspace completely.

---

## 🛠️ System Prerequisites
Ensure your Raspberry Pi OS system layout is up to date and has the correct GTK Core drawing libraries installed:
```bash
sudo apt update
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 wvkbd
```

---

## 🚀 Installation & Folder Directory Deployment

To organize and run the files exactly how they are structured in this repository, follow these quick terminal commands:

1. Create and step into your local production directory folder workspace on your Pi:
   ```bash
   mkdir -p /home/mixxx/mixxx-touch-kb-overlay
   cd /home/mixxx/mixxx-touch-kb-overlay
   ```
2. Clone or place the repository configuration files (`floating-touch-button.py`, `mixxx-kb-toggle.sh`, `mixxx-kb-menu-toggle.sh`, and `mixxx-kb-overlay.desktop`) directly inside that folder directory path.
3. Ensure the script lines are marked as executable system targets:
   ```bash
   chmod +x floating-touch-button.py mixxx-kb-toggle.sh mixxx-kb-menu-toggle.sh
   ```
4. Copy the Desktop Entry file directly into your local local profiles tree repository to install it directly inside the system's active Start Menu viewports:
   ```bash
   mkdir -p ~/.local/share/applications/
   cp /home/mixxx/mixxx-touch-kb-overlay/mixxx-kb-overlay.desktop ~/.local/share/applications/
   ```

---

## ⚙️ Setting Up Automation on Boot
To automate your floating gray capsule to initialize automatically every single time your user profile launches inside Labwc, add the toggle controller script execution path directly into your local desktop compositor initialization file (`~/.config/labwc/autostart`):

```bash
# Add this line at the bottom of your autostart file profile:
/home/mixxx/mixxx-touch-kb-overlay/mixxx-kb-menu-toggle.sh &
```

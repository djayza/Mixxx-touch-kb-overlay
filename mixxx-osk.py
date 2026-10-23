#!/usr/bin/env python3
"""
Mixxx on-screen keyboard for Raspberry Pi 5 (labwc / Wayland).

* A floating "KB" button and a full touch keyboard, both on the Wayland
  OVERLAY layer, so they draw ABOVE a fullscreen Mixxx window.
* The keyboard never takes keyboard focus (KeyboardMode.NONE), so Mixxx keeps
  its focus and the text box you tapped stays active.
* Keys are injected through /dev/uinput, so they work in any app (Mixxx's
  library search box, file dialogs, the browser, ...).

Button gestures
  tap            show / hide keyboard
  hold 1 s       button turns blue -> drag it where you want
  hold 3 s       quit the overlay (without moving)

Running the script a second time stops the running copy (menu toggle).
"""
import os
import signal
import subprocess
import sys
import time

os.environ["GDK_BACKEND"] = "wayland"

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib  # noqa: E402

try:
    from evdev import UInput, ecodes as e
except ImportError:
    sys.exit("python3-evdev is missing:  sudo apt install python3-evdev")

PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "mixxx-osk.pid")


# --------------------------------------------------------------------------
# single instance / toggle
# --------------------------------------------------------------------------
def toggle_running_instance():
    try:
        pid = int(open(PIDFILE).read().strip())
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            if b"mixxx-osk" not in f.read():
                return
        os.kill(pid, signal.SIGTERM)
        sys.exit(0)
    except (OSError, ValueError):
        return


# --------------------------------------------------------------------------
# key injection (uinput)
# --------------------------------------------------------------------------
UNSHIFTED = {
    "-": "MINUS", "=": "EQUAL", "[": "LEFTBRACE", "]": "RIGHTBRACE",
    ";": "SEMICOLON", "'": "APOSTROPHE", ",": "COMMA", ".": "DOT",
    "/": "SLASH", "\\": "BACKSLASH", "`": "GRAVE", " ": "SPACE",
}
SHIFTED = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7",
    "*": "8", "(": "9", ")": "0", "_": "MINUS", "+": "EQUAL",
    "{": "LEFTBRACE", "}": "RIGHTBRACE", ":": "SEMICOLON", '"': "APOSTROPHE",
    "<": "COMMA", ">": "DOT", "?": "SLASH", "|": "BACKSLASH", "~": "GRAVE",
}


def char_to_key(ch):
    """Return (keycode, needs_shift) for a US-layout character."""
    if ch.isalpha() and ch.isascii():
        return getattr(e, "KEY_" + ch.upper()), ch.isupper()
    if ch.isdigit():
        return getattr(e, "KEY_" + ch), False
    if ch in UNSHIFTED:
        return getattr(e, "KEY_" + UNSHIFTED[ch]), False
    if ch in SHIFTED:
        return getattr(e, "KEY_" + SHIFTED[ch]), True
    return None, False


class Typist:
    def __init__(self):
        self.ui = UInput(
            {e.EV_KEY: list(range(1, 249))}, name="mixxx-osk-keyboard"
        )
        time.sleep(0.4)  # let the compositor pick the new device up

    def tap(self, code, shift=False, ctrl=False):
        mods = []
        if ctrl:
            mods.append(e.KEY_LEFTCTRL)
        if shift:
            mods.append(e.KEY_LEFTSHIFT)
        for m in mods:
            self.ui.write(e.EV_KEY, m, 1)
        self.ui.write(e.EV_KEY, code, 1)
        self.ui.syn()
        self.ui.write(e.EV_KEY, code, 0)
        for m in reversed(mods):
            self.ui.write(e.EV_KEY, m, 0)
        self.ui.syn()


# --------------------------------------------------------------------------
# keyboard layout
#   each row: list of (kind, value, width-in-columns); 12 columns per row
# --------------------------------------------------------------------------
def C(ch, w=1):
    return ("char", ch, w)


MAIN = [
    [("esc", "Esc", 1)] + [C(c) for c in "1234567890"] + [("bksp", "⌫", 1)],
    [("tab", "Tab", 1)] + [C(c) for c in "qwertyuiop"] + [C("-")],
    [C(c) for c in "asdfghjkl"] + [("enter", "Enter", 3)],
    [("shift", "⇧", 2)] + [C(c) for c in "zxcvbnm"] + [C(","), C("."), C("'")],
    [("sym", "?123", 1), ("find", "Find", 1), ("move", "⇅", 1),
     ("space", "space", 4),
     ("left", "←", 1), ("down", "↓", 1), ("up", "↑", 1), ("right", "→", 1),
     ("hide", "Hide", 1)],
]

SYMBOLS = [
    [("esc", "Esc", 1)] + [C(c) for c in "!@#$%^&*()"] + [("bksp", "⌫", 1)],
    [("tab", "Tab", 1)] + [C(c) for c in "[]{}<>=+_-|"],
    [C(c) for c in "~`:;\"'?/\\"] + [("enter", "Enter", 3)],
    [("sym", "ABC", 2)] + [C(c) for c in ",.!?@#$%&*"],
    MAIN[4],
]

SPECIAL_CODES = {
    "esc": e.KEY_ESC, "tab": e.KEY_TAB, "enter": e.KEY_ENTER,
    "bksp": e.KEY_BACKSPACE, "space": e.KEY_SPACE,
    "left": e.KEY_LEFT, "right": e.KEY_RIGHT, "up": e.KEY_UP,
    "down": e.KEY_DOWN,
}
REPEATING = {"bksp", "left", "right", "up", "down"}

CSS = b"""
window.osk { background-color: rgba(18,20,24,0.97); }
button.key {
    background-image: none; background-color: #2d323a; color: #ffffff;
    border: 1px solid #4a505a; border-radius: 9px; box-shadow: none;
    min-height: 54px; padding: 0; font-size: 21px; font-weight: bold;
}
button.key.mod { background-color: #3b414c; font-size: 17px; }
button.key.on  { background-color: #ff9a2e; color: #000000; }
button.key:active { background-color: #3d8bff; color: #ffffff; }
"""


class Keyboard(Gtk.Window):
    def __init__(self, typist):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.typist = typist
        self.shift = "off"      # off | once | caps
        self.symbols = False
        self.at_bottom = True
        self.repeat_delay_id = None
        self.repeat_id = None

        self.get_style_context().add_class("osk")
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self, "mixxx-osk")
        # NONE: never steal keyboard focus from Mixxx
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_exclusive_zone(self, 0)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        self._apply_vertical_anchor()

        self.set_focus_on_map(False)
        self.set_accept_focus(False)
        self.grid = None
        self.rebuild()

    # ---- layout -----------------------------------------------------------
    def _apply_vertical_anchor(self):
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, self.at_bottom)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, not self.at_bottom)

    def rebuild(self):
        if self.grid is not None:
            self.remove(self.grid)
            self.grid.destroy()
        self.grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=True,
                             column_spacing=6, row_spacing=6)
        self.grid.set_margin_start(8)
        self.grid.set_margin_end(8)
        self.grid.set_margin_top(8)
        self.grid.set_margin_bottom(8)
        rows = SYMBOLS if self.symbols else MAIN
        for r, row in enumerate(rows):
            col = 0
            for kind, value, width in row:
                btn = self._make_key(kind, value)
                self.grid.attach(btn, col, r, width, 1)
                col += width
        self.add(self.grid)
        self.grid.show_all()

    def _make_key(self, kind, value):
        if kind == "char":
            letter = value.isalpha() and not self.symbols
            label = value.upper() if (letter and self.shift != "off") else value
        else:
            label = value
        btn = Gtk.Button()
        lab = Gtk.Label(label=label)
        btn.add(lab)
        btn.set_focus_on_click(False)
        btn.set_can_focus(False)
        ctx = btn.get_style_context()
        ctx.add_class("key")
        if kind != "char":
            ctx.add_class("mod")
        if kind == "shift" and self.shift != "off":
            ctx.add_class("on")
            lab.set_text("⇪" if self.shift == "caps" else "⇧")
        if kind == "sym" and self.symbols:
            ctx.add_class("on")
        btn.connect("pressed", self.on_key_pressed, kind, value)
        btn.connect("released", self.on_key_released)
        return btn

    # ---- input ------------------------------------------------------------
    def on_key_pressed(self, _btn, kind, value):
        if kind == "char":
            code, need_shift = char_to_key(value)
            if code is None:
                return
            if value.isalpha() and not self.symbols:
                need_shift = self.shift != "off"
            self.typist.tap(code, shift=need_shift)
            if self.shift == "once":
                self.shift = "off"
                GLib.idle_add(self.rebuild)
        elif kind in SPECIAL_CODES:
            self.typist.tap(SPECIAL_CODES[kind])
            if kind in REPEATING:
                self._start_repeat(SPECIAL_CODES[kind])
        elif kind == "find":
            # Mixxx: Ctrl+F focuses the library search box
            self.typist.tap(e.KEY_F, ctrl=True)
        elif kind == "shift":
            self.shift = {"off": "once", "once": "caps", "caps": "off"}[self.shift]
            GLib.idle_add(self.rebuild)
        elif kind == "sym":
            self.symbols = not self.symbols
            GLib.idle_add(self.rebuild)
        elif kind == "move":
            self.at_bottom = not self.at_bottom
            self._apply_vertical_anchor()
        elif kind == "hide":
            self.hide()

    def on_key_released(self, *_):
        self._stop_repeat()

    def _start_repeat(self, code):
        self._stop_repeat()

        def begin():
            self.repeat_id = GLib.timeout_add(70, lambda: (self.typist.tap(code), True)[1])
            self.repeat_delay_id = None
            return False

        self.repeat_delay_id = GLib.timeout_add(400, begin)

    def _stop_repeat(self):
        for attr in ("repeat_delay_id", "repeat_id"):
            sid = getattr(self, attr)
            if sid is not None:
                GLib.source_remove(sid)
                setattr(self, attr, None)

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()


# --------------------------------------------------------------------------
# floating button
# --------------------------------------------------------------------------
class FloatingButton(Gtk.Window):
    SIZE = 70

    def __init__(self, keyboard):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.keyboard = keyboard

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self, "mixxx-osk-button")
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_exclusive_zone(self, -1)  # ignore other surfaces' zones
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)
        self.set_size_request(self.SIZE, self.SIZE)
        self.set_accept_focus(False)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        self.x, self.y = 150, 150
        self._apply_margins()

        self.pressed = False
        self.unlocked = False
        self.dragging = False
        self.press_t = 0.0
        self.sx = self.sy = 0.0
        self.t_unlock = None
        self.t_quit = None

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_press)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("button-release-event", self.on_release)

    def _apply_margins(self):
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, self.x)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, self.y)

    def on_draw(self, _w, cr):
        cr.set_operator(cairo.Operator.SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)
        if self.unlocked:
            cr.set_source_rgba(0.2, 0.6, 1.0, 0.95)
        elif self.pressed:
            cr.set_source_rgba(0.2, 0.2, 0.2, 0.95)
        elif self.keyboard.get_visible():
            cr.set_source_rgba(0.85, 0.5, 0.1, 0.9)
        else:
            cr.set_source_rgba(0.35, 0.35, 0.35, 0.85)
        c = self.SIZE / 2
        cr.arc(c, c, c - 3, 0, 6.2831853)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.95)
        cr.set_line_width(3)
        cr.stroke()
        cr.select_font_face("DejaVu Sans", cairo.FontSlant.NORMAL,
                            cairo.FontWeight.BOLD)
        cr.set_font_size(18)
        ext = cr.text_extents("KB")
        cr.move_to(c - ext.width / 2 - ext.x_bearing,
                   c - ext.height / 2 - ext.y_bearing)
        cr.show_text("KB")
        return False

    def _cancel_timers(self):
        for attr in ("t_unlock", "t_quit"):
            sid = getattr(self, attr)
            if sid is not None:
                GLib.source_remove(sid)
                setattr(self, attr, None)

    def _unlock(self):
        self.unlocked = True
        self.t_unlock = None
        self.queue_draw()
        return False

    def _quit(self):
        self.t_quit = None
        if not self.dragging:
            Gtk.main_quit()
        return False

    def on_press(self, _w, ev):
        if ev.button != 1:
            return False
        self.press_t = time.time()
        self.pressed = True
        self.unlocked = False
        self.dragging = False
        self.sx, self.sy = ev.x, ev.y
        self._cancel_timers()
        self.t_unlock = GLib.timeout_add(1000, self._unlock)
        self.t_quit = GLib.timeout_add(3000, self._quit)
        self.queue_draw()
        return True

    def on_motion(self, _w, ev):
        if not self.unlocked:
            return False
        dx, dy = ev.x - self.sx, ev.y - self.sy
        if not self.dragging and (abs(dx) > 4 or abs(dy) > 4):
            self.dragging = True
            if self.t_quit is not None:
                GLib.source_remove(self.t_quit)
                self.t_quit = None
        if self.dragging:
            self.x = max(0, int(self.x + dx))
            self.y = max(0, int(self.y + dy))
            self._apply_margins()
        return True

    def on_release(self, _w, ev):
        if ev.button != 1:
            return False
        self._cancel_timers()
        was_tap = (not self.dragging and not self.unlocked
                   and time.time() - self.press_t < 0.4)
        self.pressed = False
        self.unlocked = False
        self.dragging = False
        if was_tap:
            self.keyboard.toggle()
        self.queue_draw()
        return True


# --------------------------------------------------------------------------
def main():
    toggle_running_instance()
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        typist = Typist()
    except (PermissionError, OSError) as err:
        subprocess.run(["notify-send", "Mixxx OSK",
                        f"Cannot open /dev/uinput: {err}"], check=False)
        sys.exit(f"Cannot open /dev/uinput ({err}). Run install.sh, then log out/in.")

    css = Gtk.CssProvider()
    css.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    keyboard = Keyboard(typist)      # created first ...
    button = FloatingButton(keyboard)  # ... so the button maps above it
    button.show_all()

    # keep the button's colour in sync with the keyboard visibility
    keyboard.connect("show", lambda *_: button.queue_draw())
    keyboard.connect("hide", lambda *_: button.queue_draw())

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
    try:
        Gtk.main()
    finally:
        try:
            os.remove(PIDFILE)
        except OSError:
            pass


if __name__ == "__main__":
    main()

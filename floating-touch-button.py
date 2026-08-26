#!/usr/bin/env python3
import sys
import subprocess
import time
import os
import cairo

# Enforce true native Wayland initialization protocols
os.environ["GDK_BACKEND"] = "wayland"

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib

class PureWaylandTouchSurface(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        
        # 1. Initialize native Wayland Layer Shell overlay mapping
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self, "touch-kb-trigger")
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        
        # 2. Anchor strictly to Top-Left margins
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)
        
        # Rigid capsule boundary dimension profiles
        self.width = 70
        self.height = 70
        self.set_size_request(self.width, self.height)
        
        # Support true window alpha transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        # Permanent tracking coordinates stored safely in memory
        self.current_x = 150
        self.current_y = 150
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, self.current_x)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, self.current_y)

        # Operational tracking flags
        self.press_time = 0
        self.drag_unlock_timer_id = None
        self.vanish_timer_id = None
        
        self.drag_unlocked = False
        self.is_dragging = False
        self.is_pressed = False
        
        self.start_mouse_x = 0
        self.start_mouse_y = 0
        self.start_margin_x = 0
        self.start_margin_y = 0

        # Bind hardware events directly to the window surface canvas
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("button-release-event", self.on_button_release)
        
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)

    def on_draw(self, widget, cr):
        """Draws the gray AssistiveTouch circle graphic natively on the canvas surface"""
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        # Circle Fill (translucent grays)
        if self.drag_unlocked:
            cr.set_source_rgba(0.2, 0.6, 1.0, 0.8) # Translucent light blue when unlocked
        elif self.is_pressed:
            cr.set_source_rgba(0.3, 0.3, 0.3, 0.8) # Darker gray on tap
        else:
            cr.set_source_rgba(0.15, 0.15, 0.15, 0.7) # Beautiful translucent dark gray
            
        cr.arc(35, 35, 32, 0, 2 * 3.1415926)
        cr.fill_preserve()

        # Crisp White Outer Ring Border Outline
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.8)
        cr.set_line_width(3)
        cr.stroke()

        # Text Rendering ('KB')
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.9) # Clean white text
        cr.select_font_face("DejaVu Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
        cr.set_font_size(18)
        
        extents = cr.text_extents("KB")
        cr.move_to(35 - extents.width/2 - extents.x_bearing, 35 - extents.height/2 - extents.y_bearing)
        cr.show_text("KB")
        return False

    def on_drag_unlock_timeout(self):
        """Triggers precisely after holding for 1 second to unlock dragging"""
        self.drag_unlocked = True
        self.queue_draw() # Trigger repaint to show unlock color
        print("Drag Lock Unlocked: Ready to reposition.")
        return False

    def on_long_press_vanish_timeout(self):
        """Triggers after holding for 3 seconds without dragging to hide completely"""
        if not self.is_dragging:
            print("3-Second long press validated. Hiding component interface.")
            subprocess.Popen(["pkill", "-x", "wvkbd-mobintl"])
            self.destroy()
            sys.exit(0)
        return False

    def on_button_press(self, widget, event):
        if event.button == 1:
            self.press_time = time.time()
            self.is_dragging = False
            self.drag_unlocked = False
            self.is_pressed = True
            self.queue_draw()
            
            # Lock coordinates footprint maps
            self.start_mouse_x = event.x_root
            self.start_mouse_y = event.y_root
            self.start_margin_x = self.current_x
            self.start_margin_y = self.current_y
            
            # Start the 1-second drag unlock countdown
            self.cancel_timers()
            self.drag_unlock_timer_id = GLib.timeout_add(1000, self.on_drag_unlock_timeout)
            
            # Start the 3-second vanish countdown
            self.vanish_timer_id = GLib.timeout_add(3000, self.on_long_press_vanish_timeout)
            return True
        return False

    def on_motion_notify(self, widget, event):
        dx = event.x_root - self.start_mouse_x
        dy = event.y_root - self.start_mouse_y
        
        if self.drag_unlocked:
            if abs(dx) > 5 or abs(dy) > 5:
                self.is_dragging = True
                if self.vanish_timer_id is not None:
                    GLib.source_remove(self.vanish_timer_id)
                    self.vanish_timer_id = None
            
            if self.is_dragging:
                temp_x = max(0, int(self.start_margin_x + dx))
                temp_y = max(0, int(self.start_margin_y + dy))
                
                GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, temp_x)
                GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, temp_y)
                return True
        return False

    def on_button_release(self, widget, event):
        if event.button == 1:
            self.is_pressed = False
            self.cancel_timers()
            
            if self.is_dragging and self.drag_unlocked:
                dx = event.x_root - self.start_mouse_x
                dy = event.y_root - self.start_mouse_y
                self.current_x = max(0, int(self.start_margin_x + dx))
                self.current_y = max(0, int(self.start_margin_y + dy))
            else:
                duration = time.time() - self.press_time
                if duration < 0.4:
                    subprocess.Popen(["/home/mixxx/mixxx-kb-toggle.sh"])
            
            self.is_dragging = False
            self.drag_unlocked = False
            self.queue_draw() # Reset color back to gray
            return True
        return False

    def cancel_timers(self):
        if self.drag_unlock_timer_id is not None:
            GLib.source_remove(self.drag_unlock_timer_id)
            self.drag_unlock_timer_id = None
        if self.vanish_timer_id is not None:
            GLib.source_remove(self.vanish_timer_id)
            self.vanish_timer_id = None

if __name__ == "__main__":
    win = PureWaylandTouchSurface()
    win.show_all()
    Gtk.main()

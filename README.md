# OpenGL-Notifier
A Blender add-on that watches Viewport (OpenGL) renders and sends:

- Live-updating Discord embed cards 📊
- Desktop notifications (Windows/macOS/Linux)
- Final "Render Complete" or "Render Canceled" alerts
- Custom sound support
- Custom Discord avatar and user name support

Supports:
- Viewport Render Image
- Viewport Render Animation

Drag `OpenGL_Notifier.py` into Blender:
Edit → Preferences → Add-ons → Install

You will now have two new menu items in each viewport's View menu:
- Viewport Render Image (with Notifications)
- Viewport Render Animation (with Notifications)

Windows users may have to enable BurnInToast notifications to receive popup notifications. The add-on should display directions (for Windows users only) within Blender's Preferences window that details how to use PowerShell to do this.

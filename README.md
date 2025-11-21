# OpenGL-Notifier
A Blender add-on that watches Viewport (OpenGL) renders and sends:

- Live-updating Discord embed cards 📊 (blue when rendering, green when complete, red when cancelled)
- Sends a separate Completed / Cancelled message
- Desktop notifications (Windows/macOS/Linux)
- Final "Render Complete" or "Render Canceled" alerts
- Custom sound support (mp3, wav, flac, etc)
- Custom Discord avatar and user name support

Supports:
- Viewport Render Image
- Viewport Render Animation
- Re-rendering by referencing the render start time (avoiding false "complete" messages)

Progress cards contain:
- Frame Range
- Total Frames
- Current Frame
- Progress %
- Last Frame Time
- Average Per Frame
- ETA Remaining
- Time Elapsed
- Sidebar color coding
  - Blue sidebar while rendering
  - Green sidebar + “Complete” when finished
  - Red sidebar + “Canceled” if the job stops mid-render

Installation:
Drag `OpenGL_Notifier.py` into Blender:
Edit → Preferences → Add-ons → Install

You will now have two new menu items in each viewport's View menu:
- Viewport Render Image (with Notifications)
- Viewport Render Animation (with Notifications)
When you click either of these:
1. The watcher arms itself
2. The render begins
3. Discord immediately receives a “starting render” embed

Progress updates are sent on a timer

Completion or cancellation sends a final “ding” message

Windows
Users may have to enable BurnInToast notifications to receive popup notifications. The add-on should display directions (for Windows users only) within Blender's Preferences window that details how to use PowerShell to do this. Or follow the instructions below. 

To install BurnInToast, open Windows PowerShell and paste this:
  Install-Module BurntToast -Scope CurrentUser -Force
If PowerShell blocks this, enable local scripts with:
  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
Then run the first command again.
To disable local scripts again, run:
  Set-ExecutionPolicy Restricted -Scope CurrentUser -Force

macOS
- Uses Notification Center through osascript
- No extra setup requiredLinux is set to use notify-send.

Linux
- Uses notify-send
- Requires libnotify on most distros

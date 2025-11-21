bl_info = {
    "name": "OpenGL Notifier (Discord + Desktop Notifications)",
    "author": "Josh Anderson + ChatGPT",
    "version": (1, 1, 4),
    "blender": (4, 0, 0),
    "location": "Edit > Preferences > Add-ons > This Add-on",
    "description": "Watches OpenGL/Viewport renders; sends desktop alerts + Discord progress/completion",
    "category": "Render",
}

import bpy, time, platform, subprocess, shutil, json, urllib.request, urllib.error, os
from bpy.types import AddonPreferences, Operator
from bpy.props import StringProperty, BoolProperty, FloatProperty
from pathlib import Path

# ---------------------------
# Helpers: prefs access
# ---------------------------
def _addon_idname():
    # When installed as an addon, __name__ is the module name. Fallbacks help in dev.
    try:
        return __name__
    except Exception:
        return "opengl_notifier"

def _prefs():
    aid = _addon_idname()
    return bpy.context.preferences.addons[aid].preferences

# ---------------------------
# Discord + Desktop notify
# ---------------------------
    
def _notify_local(msg):
    prefs = _prefs()

    # Sound (Windows)
    if prefs.enable_sound:
        if prefs.enable_custom_sound and prefs.custom_sound_path:
            _play_custom_sound(prefs.custom_sound_path)
        else:
            _play_only_sound()

    # Popup (Windows)
    if prefs.enable_toast:
        _popup_only(msg)

def _notify_local(msg):
    pf = _prefs()

    # --- Sound ---
    if pf.enable_sound:
        if pf.enable_custom_sound and pf.custom_sound_path:
            _play_custom_sound(pf.custom_sound_path)
        else:
            _play_only_sound()

    # --- Popup ---
    if pf.enable_toast:
        _popup_only(msg)


# Operating System Dependent Notifications

def _play_only_sound():
    """Simple cross-platform notification sound."""
    try:
        sys = platform.system()
        if sys == "Windows":
            import winsound
            winsound.Beep(880, 300)  # single beep

        elif sys == "Darwin":
            # macOS: play a stock system sound if afplay exists
            if shutil.which("afplay"):
                subprocess.Popen(
                    ["afplay", "/System/Library/Sounds/Glass.aiff"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        elif sys == "Linux":
            # Linux: try paplay (PulseAudio) or aplay (ALSA) with a standard sound
            if shutil.which("paplay"):
                # freedesktop sound theme (often available)
                sound = "/usr/share/sounds/freedesktop/stereo/complete.oga"
                if os.path.isfile(sound):
                    subprocess.Popen(
                        ["paplay", sound],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            elif shutil.which("aplay"):
                # ALSA example sound (not guaranteed, but common)
                sound = "/usr/share/sounds/alsa/Front_Center.wav"
                if os.path.isfile(sound):
                    subprocess.Popen(
                        ["aplay", sound],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
    except Exception:
        pass

def _play_custom_sound(path: str):
    """Windows + macOS + Linux: play a user-selected audio file (mp3/wav/flac)."""
    if not path or not os.path.isfile(path):
        return

    # Try ffplay first (works on Windows, macOS, many Linux setups)
    if shutil.which("ffplay"):
        subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    sys = platform.system()

    # macOS: use afplay directly on the chosen file
    if sys == "Darwin":
        if shutil.which("afplay"):
            subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return

    # Linux: use paplay or aplay on the chosen file
    if sys == "Linux":
        if shutil.which("paplay"):
            subprocess.Popen(
                ["paplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif shutil.which("aplay"):
            subprocess.Popen(
                ["aplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return

    # Windows: PowerShell MediaPlayer, wait roughly for file duration (max 30s)
    if sys == "Windows":
        try:
            from pathlib import Path as _P
            uri = _P(path).resolve().as_uri()  # e.g. file:///C:/Users/...

            ps = (
                "$u='" + uri + "';"
                "Add-Type -AssemblyName PresentationCore;"
                "$m=New-Object System.Windows.Media.MediaPlayer;"
                "$m.Open([uri]$u); $m.Play();"
                "$max=[datetime]::UtcNow.AddSeconds(30);"
                "while(-not $m.NaturalDuration.HasTimeSpan -and [datetime]::UtcNow -lt $max){ Start-Sleep -Milliseconds 100 }"
                "if($m.NaturalDuration.HasTimeSpan){"
                "  $dur=$m.NaturalDuration.TimeSpan.TotalSeconds;"
                "  Start-Sleep -Seconds ([Math]::Min([double]$dur,30));"
                "} else { Start-Sleep -Seconds 2 }"
            )

            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print("[OpenGL Notifier] Custom sound failed:", e)

def _popup_only(msg="OpenGL Render Complete"):
    """Desktop popup: Windows via BurntToast; macOS via Notification Center; Linux via notify-send."""
    sys = platform.system()

    if sys == "Windows":
        try:
            safe = msg.replace("'", "''")
            ps = (
                "try { Import-Module BurntToast -ErrorAction Stop; "
                "New-BurntToastNotification -Text '" + safe + "' ; exit 0 } "
                "catch { exit 0 }"
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    elif sys == "Darwin":
        # macOS: use AppleScript to show a notification
        try:
            safe = msg.replace('"', '\\"')
            cmd = f'display notification "{safe}" with title "Blender (OpenGL Notifier)"'
            subprocess.Popen(
                ["osascript", "-e", cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    elif sys == "Linux":
        # Linux: use notify-send if available
        try:
            if shutil.which("notify-send"):
                subprocess.Popen(
                    ["notify-send", "Blender (OpenGL Notifier)", msg],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass

# --- Discord post (balanced try/except, with clear logs) ---
def _post_discord(content: str):
    prefs = _prefs()
    url = (prefs.webhook_url or "").strip()
    if not prefs.enable_discord or not url:
        return

    payload = {"username": prefs.discord_username, "content": content}
    ava = (prefs.discord_avatar_url or "").strip()
    if ava:
        payload["avatar_url"] = ava

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        # Look like a real browser to avoid Cloudflare 1010
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
    }

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.getcode()
            print(f"[OpenGL Notifier] Discord HTTP {code}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"[OpenGL Notifier] Discord HTTPError {e.code}: {body}")
    except urllib.error.URLError as e:
        print(f"[OpenGL Notifier] Discord URLError: {e.reason}")
    except Exception as e:
        print("[OpenGL Notifier] Discord unexpected error:", e)

# ---------------------------
# Discord embeds (live-updating card)
# ---------------------------

_BLUE  = 0x1E88E5  # in-progress color
_GREEN = 0x43A047  # completed color
_RED   = 0xE53935  # canceled / error color

def _discord_build_embed(stage: str, stats: dict) -> dict:
    """Build a Discord embed for start/progress/done."""
    job_label   = stats.get("job_label", "Viewport Render")
    job_type    = stats.get("job_type", "Animation")
    total       = stats.get("total_frames", 0)
    first_f     = stats.get("first_frame", 0)
    last_f      = stats.get("last_frame", 0)
    current     = stats.get("current_frame", 0)
    progress    = stats.get("progress_str", "—")
    frame_time  = stats.get("last_frame_time_str", "—")
    avg_time    = stats.get("avg_time_str", "—")
    eta         = stats.get("eta_str", "—")
    elapsed     = stats.get("elapsed_str", "—")
    total_elapsed = stats.get("total_elapsed_str", "—")

    if stage == "start":
        title = f"{job_label} — Render starting"
        desc  = f"Job type: {job_type}\nFrames: {total} | Range: {first_f}–{last_f}"
        color = _BLUE

    elif stage == "done":
        title = f"{job_label} — Complete"
        desc  = f"Job type: {job_type}"
        color = _GREEN

    elif stage == "canceled":
        title = f"{job_label} — Render canceled ⛔"
        desc  = f"Job type: {job_type}\nRender appears to have been canceled or interrupted."
        color = _RED

    else:
        # progress
        title = f"{job_label} — Rendering…"
        desc  = f"Job type: {job_type}"
        color = _BLUE

    fields = [
        {"name": "Frame Range",        "value": f"{first_f}–{last_f}",    "inline": True},
        {"name": "Total frames",       "value": str(total),               "inline": True},
        {"name": "Current frame",      "value": str(current),             "inline": True},
        {"name": "Progress",           "value": progress,                 "inline": False},
        {"name": "Last frame time",    "value": frame_time,               "inline": True},
        {"name": "Average per frame",  "value": avg_time,                 "inline": True},
        {"name": "ETA (remaining)",    "value": eta,                      "inline": True},
        {"name": "Time elapsed",       "value": elapsed,                  "inline": True},
    ]

    return {
        "title": title,
        "description": desc,
        "color": color,
        "fields": fields,
    }


def _discord_post_embed(embed: dict):
    """Create a new Discord message with an embed. Returns message_id or None."""
    prefs = _prefs()
    url = (prefs.webhook_url or "").strip()
    if not prefs.enable_discord or not url:
        return None

    payload = {"username": prefs.discord_username, "embeds": [embed]}
    ava = (prefs.discord_avatar_url or "").strip()
    if ava:
        payload["avatar_url"] = ava

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
    }

    # Ask Discord to return the created message so we can grab its ID
    url_wait = url + "?wait=true"

    try:
        req = urllib.request.Request(url_wait, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="ignore") or "{}"
            try:
                js = json.loads(body)
                msg_id = js.get("id")
                print(f"[OpenGL Notifier] Discord embed created, id={msg_id}")
                return msg_id
            except Exception:
                print("[OpenGL Notifier] Discord: could not parse message id")
                return None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"[OpenGL Notifier] Discord HTTPError (embed POST) {e.code}: {body}")
    except urllib.error.URLError as e:
        print(f"[OpenGL Notifier] Discord URLError (embed POST): {e.reason}")
    except Exception as e:
        print("[OpenGL Notifier] Discord unexpected error (embed POST):", e)

    return None


def _discord_edit_embed(message_id: str, embed: dict):
    """Edit an existing Discord message (live update of the same card)."""
    if not message_id:
        return

    prefs = _prefs()
    base_url = (prefs.webhook_url or "").strip()
    if not prefs.enable_discord or not base_url:
        return

    url = f"{base_url}/messages/{message_id}"
    payload = {"username": prefs.discord_username, "embeds": [embed]}
    ava = (prefs.discord_avatar_url or "").strip()
    if ava:
        payload["avatar_url"] = ava

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
    }

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="PATCH")
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.getcode()
            print(f"[OpenGL Notifier] Discord embed edited HTTP {code}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"[OpenGL Notifier] Discord HTTPError (embed PATCH) {e.code}: {body}")
    except urllib.error.URLError as e:
        print(f"[OpenGL Notifier] Discord URLError (embed PATCH): {e.reason}")
    except Exception as e:
        print("[OpenGL Notifier] Discord unexpected error (embed PATCH):", e)

# ---------------------------
# Core watcher
# ---------------------------
def _human_secs(s: float) -> str:
    if s is None or s < 0:
        return "—"
    m, sec = divmod(int(s), 60)
    h, m   = divmod(m, 60)
    if h:   return f"{h:d}h {m:02d}m {sec:02d}s"
    if m:   return f"{m:d}m {sec:02d}s"
    return f"{sec:d}s"

def _expected_paths(scene, r, animation: bool):
    frames = range(scene.frame_start, scene.frame_end + 1) if animation else [scene.frame_current]
    return [Path(bpy.path.abspath(r.frame_path(frame=f))) for f in frames]

def _count_completed(paths, start_time):
    """Count frames that exist, are non-empty, and were written in this run."""
    n = 0
    for p in paths:
        try:
            if p.exists():
                st = p.stat()
                if st.st_size > 0 and st.st_mtime >= start_time:
                    n += 1
        except Exception:
            pass
    return n

# State kept at module level for the timer
_STATE = {
    "armed": False,
    "animation": True,
    "expected": [],
    "expected_count": 0,
    "first_frame": 0,
    "last_frame": 0,
    "last_path": None,
    "last_size_time": (None, 0.0),
    "start_time": 0.0,
    "started_posted": False,
    "last_progress_post": 0.0,
    "prev_exist_count": 0,
    "frame_times": [],
    "last_frame_t0": None,
    "discord_message_id": None,
    "job_label": "",
}

def _watcher_timer():
    pf = _prefs()
    now = time.time()

    CANCEL_IDLE_MIN    = 120.0   # at least 2 minutes idle
    CANCEL_IDLE_FACTOR = 5.0    # or 5x the average frame time, whichever is larger

    if not _STATE["armed"]:
        return None  # shouldn't happen

    expected       = _STATE["expected"]
    expected_count = _STATE["expected_count"]
    last_path      = _STATE["last_path"]
    start_time     = _STATE["start_time"]
    last_size, last_t = _STATE["last_size_time"]
    started_posted = _STATE["started_posted"]

    # 1) detect real progress (non-empty file modified after arm)
    progress_started = any(
        (p.exists() and p.stat().st_size > 0 and p.stat().st_mtime >= start_time)
        for p in expected
    )

    # Count completed now so stats are always ready
    exist_count = _count_completed(expected, start_time)
    all_present = (exist_count >= expected_count)

    # log per-frame time when a new file appears
    if exist_count > _STATE["prev_exist_count"]:
        if _STATE["last_frame_t0"] is not None:
            _STATE["frame_times"].append(now - _STATE["last_frame_t0"])
        _STATE["last_frame_t0"]   = now
        _STATE["prev_exist_count"] = exist_count

    # If nothing has started, just keep waiting
    if not progress_started:
        return pf.check_interval

    job_type  = "Animation" if _STATE["animation"] else "Single Frame"
    job_label = _STATE["job_label"]

    # Shared timing stats
    avg = (sum(_STATE["frame_times"]) / len(_STATE["frame_times"])) if _STATE["frame_times"] else None
    remaining = max(expected_count - exist_count, 0)
    eta = (avg * remaining) if (avg is not None) else None
    cur_frame_num = _STATE["first_frame"] + exist_count - 1 if _STATE["animation"] else bpy.context.scene.frame_current
    last_frame_time = _STATE["frame_times"][-1] if _STATE["frame_times"] else None
    elapsed = now - start_time
    pct = (exist_count / expected_count * 100.0) if expected_count else 100.0
    progress_str = f"{exist_count}/{expected_count} ({pct:.1f}%)" if expected_count else "—"

    stats = {
        "job_label": job_label,
        "job_type": job_type,
        "total_frames": expected_count,
        "first_frame": _STATE["first_frame"],
        "last_frame": _STATE["last_frame"],
        "current_frame": cur_frame_num,
        "progress_str": progress_str,
        "last_frame_time_str": _human_secs(last_frame_time),
        "avg_time_str": _human_secs(avg),
        "eta_str": _human_secs(eta),
        "elapsed_str": _human_secs(elapsed),
        "total_elapsed_str": _human_secs(elapsed),
    }

    # --- Cancellation heuristic: treat as canceled if very idle mid-job ---
    # Only applies after at least one frame is done and before all are present.
    if _STATE["frame_times"] and _STATE["last_frame_t0"] is not None and not (all_present):
        idle = now - _STATE["last_frame_t0"]
        if avg is not None and avg > 0:
            idle_threshold = max(CANCEL_IDLE_MIN, CANCEL_IDLE_FACTOR * avg)
        else:
            idle_threshold = CANCEL_IDLE_MIN

        if idle >= idle_threshold:
            # treat as canceled or interrupted
            total_elapsed = now - start_time
            stats["elapsed_str"]       = _human_secs(total_elapsed)
            stats["total_elapsed_str"] = _human_secs(total_elapsed)

            print("[OpenGL Notifier] Viewport render appears canceled or interrupted.")
            _notify_local("Viewport render canceled")

            if pf.enable_discord:
                # "canceled" stage → red embed, explanatory text
                embed = _discord_build_embed("canceled", stats)
                msg_id = _STATE.get("discord_message_id")
                if msg_id:
                    _discord_edit_embed(msg_id, embed)
                else:
                    _discord_post_embed(embed)

                # NEW: single plain text cancel message
                progress_str = stats.get("progress_str", "")
                try:
                    _post_discord(f"⛔ Viewport render canceled — {job_label} ({progress_str})")
                except Exception:
                    pass

            _STATE["armed"] = False
            return None

    # 2) First time we see progress: create the embed message
    if progress_started and not started_posted and pf.enable_discord:
        _STATE["started_posted"] = True
        _STATE["last_frame_t0"]  = now

        embed = _discord_build_embed("start", stats)
        msg_id = _discord_post_embed(embed)
        if msg_id:
            _STATE["discord_message_id"] = msg_id

    # 3) stability check for the very last frame file
    all_stable = False
    if all_present and last_path is not None and last_path.exists():
        try:
            size = last_path.stat().st_size
        except Exception:
            size = None

        if size is None or size != last_size:
            _STATE["last_size_time"] = (size, now)  # changed → reset
        else:
            if now - last_t >= pf.stable_delay:
                all_stable = True

    # 4) throttled Discord progress (while not fully complete)
    if pf.enable_discord and _STATE["started_posted"] and not (all_present and all_stable):
        if now - _STATE["last_progress_post"] >= pf.update_interval:
            # PROGRESS ONLY – note the "progress" stage
            embed = _discord_build_embed("progress", stats)
            msg_id = _STATE.get("discord_message_id")
            if msg_id:
                _discord_edit_embed(msg_id, embed)
            else:
                # If the start message failed, create one now
                msg_id = _discord_post_embed(embed)
                if msg_id:
                    _STATE["discord_message_id"] = msg_id

            _STATE["last_progress_post"] = now

    # 5) completion
    if all_present and all_stable:
        total_elapsed = now - start_time
        avg = (sum(_STATE["frame_times"]) / len(_STATE["frame_times"])) if _STATE["frame_times"] else None
        stats["avg_time_str"]        = _human_secs(avg)
        stats["elapsed_str"]         = _human_secs(total_elapsed)
        stats["total_elapsed_str"]   = _human_secs(total_elapsed)

        print("[OpenGL Notifier] Viewport render finished.")
        _notify_local("Viewport render complete")

        if pf.enable_discord:
            # Final embed → "done" stage (green bar, ✅ title)
            embed = _discord_build_embed("done", stats)
            msg_id = _STATE.get("discord_message_id")
            if msg_id:
                _discord_edit_embed(msg_id, embed)
            else:
                _discord_post_embed(embed)

            # NEW: single plain text message to trigger a fresh mobile notification
            progress_str = stats.get("progress_str", "")
            try:
                _post_discord(f"✅ Viewport render complete — {job_label} ({progress_str})")
            except Exception:
                pass

        _STATE["armed"] = False
        return None


    return pf.check_interval

# ---------------------------
# Operator to start watcher
# ---------------------------
class OPENGLNOTIFIER_OT_start(Operator):
    bl_idname = "openglnotifier.start_watcher"
    bl_label = "Start Watcher (Viewport/OpenGL)"
    bl_description = "Arm the watcher; then run your OpenGL/Viewport render"

    animation: BoolProperty(
        name="Watch Animation Range",
        description="If on, watch full frame range; if off, only current frame",
        default=True,
    )

    def execute(self, context):
        pf = _prefs()
        scene = context.scene
        r = scene.render

        expected = _expected_paths(scene, r, self.animation)
        if not expected:
            self.report({'ERROR'}, "No expected output path (check Output > File Path)")
            return {'CANCELLED'}

        raw_label = bpy.path.display_name_from_filepath(bpy.path.abspath(r.filepath)) or scene.name or "Viewport Render"

        # Strip trailing frame token hashes (e.g. "####")
        job_label = raw_label.rstrip('#').rstrip()  # removes #### ONLY at the end

        _STATE.update({
            "armed": True,
            "animation": bool(self.animation),
            "expected": expected,
            "expected_count": len(expected),
            "first_frame": scene.frame_start if self.animation else scene.frame_current,
            "last_frame": scene.frame_end if self.animation else scene.frame_current,
            "last_path": expected[-1],
            "last_size_time": (None, 0.0),
            "start_time": time.time(),
            "started_posted": False,
            "last_progress_post": 0.0,
            "prev_exist_count": 0,
            "frame_times": [],
            "last_frame_t0": None,
            "discord_message_id": None,
            "job_label": job_label,
        })

        bpy.app.timers.register(_watcher_timer, first_interval=pf.check_interval)
        self.report({'INFO'}, f"Watcher armed for {'animation' if self.animation else 'current frame'}")
        return {'FINISHED'}

# ---------------------------
# Preferences UI
# ---------------------------
class OPENGLNOTIFIER_Preferences(AddonPreferences):
    bl_idname = _addon_idname()

    webhook_url: StringProperty(
        name="Discord Webhook URL",
        description="Paste the Discord webhook URL for the channel/thread",
        default="",
    )
    discord_username: StringProperty(
        name="Discord Display Name",
        description="Name to show in Discord",
        default="OpenGL Notifier"
    )
    discord_avatar_url: StringProperty(
        name="Discord Avatar URL",
        description="Optional image URL for the webhook user",
        default="",
    )
    enable_discord: BoolProperty(
        name="Send to Discord",
        description="Post start/progress/completion to Discord",
        default=True
    )
    enable_sound: BoolProperty(
        name="Desktop Sound",
        description="Play a short sound when complete",
        default=True
    )
    enable_custom_sound: bpy.props.BoolProperty(
        name="Custom Sound",
        description="Play this audio file instead of the default beep",
        default=False
    )
    custom_sound_path: bpy.props.StringProperty(
        name="Sound File",
        description="Choose an mp3/wav/flac/etc. to play on completion",
        subtype='FILE_PATH',
        default=""
    )
    enable_toast: BoolProperty(
        name="Desktop Toast",
        description="Show a system toast/notification when complete",
        default=True
    )
    check_interval: FloatProperty(
        name="Check Interval (s)",
        description="Seconds between checks (gentle polling)",
        min=0.1, max=5.0, default=1.0
    )
    stable_delay: FloatProperty(
        name="Stable Delay (s)",
        description="How long the last frame must stop growing before considered done",
        min=0.5, max=10.0, default=1.5
    )
    update_interval: FloatProperty(
        name="Discord Update Interval (s)",
        description="Throttle progress updates to Discord",
        min=2.0, max=120.0, default=5.0
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        # --- Discord section ---
        col.label(text="Discord", icon='URL')
        col.prop(self, "webhook_url")
        col.prop(self, "discord_username")
        col.prop(self, "discord_avatar_url")

        row = col.row(align=True)
        row.prop(self, "enable_discord")

        # Test Discord button
        row = col.row(align=True)
        row.operator("openglnotifier.test_discord", icon='PLAY')
        col.separator()

        # --- Desktop Notifications section ---
        col.label(text="Desktop Notifications", icon='SPEAKER')

        row = col.row(align=True)
        row.prop(self, "enable_sound")
        row.prop(self, "enable_toast", text="Desktop Popup")

        col.prop(self, "enable_custom_sound")
        row = col.row(align=True)
        row.enabled = self.enable_custom_sound
        row.prop(self, "custom_sound_path")

        # Test buttons
        row = col.row(align=True)
        row.operator("openglnotifier.test_sound", icon='PLAY')
        row.operator("openglnotifier.test_popup", icon='PLAY')
        col.separator()

        # --- Watcher Timing section ---
        col.label(text="Watcher Timing", icon='TIME')
        row = col.row(align=True)
        row.prop(self, "check_interval")
        row.prop(self, "stable_delay")
        row.prop(self, "update_interval")
        col.separator()

        import platform
        sys = platform.system()

        # --- Windows Toast help / PowerShell instructions (Windows only) ---
        if sys == "Windows":
            help_box = col.box()
            help_box.label(text="Windows Toast Setup (PowerShell)", icon='INFO')

            help_box.label(text="If Desktop Popup is enabled but no toast appears on Windows, you may need to:")
            help_box.separator()

            # 1) Install BurntToast and test
            help_box.label(text="1) Install BurntToast for your user and test a popup:")
            hb1 = help_box.column(align=True)
            hb1.label(text="   # Run these in PowerShell")
            hb1.label(text="   Install-Module BurntToast -Scope CurrentUser -Force")
            hb1.label(text="   Import-Module BurntToast")
            hb1.label(text="   New-BurntToastNotification -Text 'Blender test', 'It worked!'")
            help_box.separator()

            # 2) Execution policy notes
            help_box.label(text="2) If PowerShell blocks scripts, you may need to allow local scripts:")
            hb2 = help_box.column(align=True)
            hb2.label(text="   # Loosen policy for your user (allows local scripts)")
            hb2.label(text="   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force")
            help_box.separator()

            help_box.label(text="3) To tighten policy again afterwards, you can restore the default:")
            hb3 = help_box.column(align=True)
            hb3.label(text="   # Restore stricter policy for your user")
            hb3.label(text="   Set-ExecutionPolicy Restricted -Scope CurrentUser -Force")

        # --- Linux hint for notify-send ---
        if sys == "Linux":
            help_box = col.box()
            help_box.label(text="Linux Notification Hint", icon='INFO')
            help_box.label(text="Desktop Popup uses `notify-send` if available.")
            help_box.label(text="If no popup appears, make sure libnotify / notify-send is installed")
            help_box.label(text="and that your desktop environment shows standard notifications.")

def execute(self, context):
    pf = _prefs()
    if pf.enable_custom_sound and pf.custom_sound_path:
        _play_custom_sound(pf.custom_sound_path)
    else:
        _play_only_sound()
    self.report({'INFO'}, "Sound test played.")
    return {'FINISHED'}

class OPENGLNOTIFIER_OT_test_discord(bpy.types.Operator):
    bl_idname = "openglnotifier.test_discord"
    bl_label = "Test Discord"
    bl_description = "Send a test message to the configured Discord webhook"

    def execute(self, context):
        pf = _prefs()
        if not pf.enable_discord:
            self.report({'WARNING'}, "Discord notifications are disabled")
            return {'CANCELLED'}
        if not pf.webhook_url.strip():
            self.report({'WARNING'}, "No Discord webhook URL set")
            return {'CANCELLED'}

        _post_discord("OpenGL Notifier: **Discord test successful**")
        self.report({'INFO'}, "Discord test sent (check your channel)")
        return {'FINISHED'}

class OPENGLNOTIFIER_OT_test_popup(bpy.types.Operator):
    bl_idname = "openglnotifier.test_popup"
    bl_label = "Test Popup"
    bl_description = "Show a test Windows popup notification"

    def execute(self, context):
        pf = _prefs()
        if not pf.enable_toast:
            self.report({'WARNING'}, "Desktop Popup is disabled")
            return {'CANCELLED'}
        _popup_only("OpenGL Notifier: Popup test successful")
        self.report({'INFO'}, "Popup test triggered")
        return {'FINISHED'}

class OPENGLNOTIFIER_OT_test_sound(bpy.types.Operator):
    bl_idname = "openglnotifier.test_sound"
    bl_label = "Test Sound"
    bl_description = "Play the selected custom sound if enabled, otherwise the default beep"

    def execute(self, context):
        pf = _prefs()
        if getattr(pf, "enable_custom_sound", False) and getattr(pf, "custom_sound_path", ""):
            _play_custom_sound(pf.custom_sound_path)
        else:
            _play_only_sound()
        self.report({'INFO'}, "Sound test played.")
        return {'FINISHED'}

# ---------------------------
# Render Menu Items
# ---------------------------

class OPENGLNOTIFIER_OT_viewport_render_notify_frame(bpy.types.Operator):
    bl_idname = "openglnotifier.viewport_render_notify_frame"
    bl_label = "Viewport Render Image (with Notifications)"
    bl_description = "Render the current viewport as an image and send notifications"

    def execute(self, context):
        # Arm watcher for single frame
        bpy.ops.openglnotifier.start_watcher(animation=False)
        # Start viewport render for current frame
        bpy.ops.render.opengl('INVOKE_DEFAULT', animation=False)
        return {'FINISHED'}

class OPENGLNOTIFIER_OT_viewport_render_notify_anim(bpy.types.Operator):
    bl_idname = "openglnotifier.viewport_render_notify_anim"
    bl_label = "Viewport Render Animation (with Notifications)"
    bl_description = "Render the viewport animation and send notifications"

    def execute(self, context):
        # Arm watcher for full frame range
        bpy.ops.openglnotifier.start_watcher(animation=True)
        # Start viewport render animation
        bpy.ops.render.opengl('INVOKE_DEFAULT', animation=True)
        return {'FINISHED'}

def opengl_notifier_view_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(
        "openglnotifier.viewport_render_notify_frame",
        text="Viewport Render Image (with Notifications)",
        icon='RENDER_STILL'
    )
    layout.operator(
        "openglnotifier.viewport_render_notify_anim",
        text="Viewport Render Animation (with Notifications)",
        icon='RENDER_ANIMATION'
    )
    layout.separator()

# ---------------------------
# Registration
# ---------------------------
CLASSES = (
    OPENGLNOTIFIER_OT_start,
    OPENGLNOTIFIER_Preferences,
    OPENGLNOTIFIER_OT_test_sound,
    OPENGLNOTIFIER_OT_test_discord,
    OPENGLNOTIFIER_OT_test_popup,
    OPENGLNOTIFIER_OT_viewport_render_notify_frame,
    OPENGLNOTIFIER_OT_viewport_render_notify_anim,
)

def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_view.append(opengl_notifier_view_menu)

def unregister():
    bpy.types.VIEW3D_MT_view.remove(opengl_notifier_view_menu)
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()

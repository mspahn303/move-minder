import json
import os
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from datetime import datetime, timedelta

try:
    import winsound
except ImportError:
    winsound = None

try:
    import winreg
except ImportError:
    winreg = None

APP_VERSION = "2.0.0"
GITHUB_REPO = "mspahn303/move-minder"

INTERVAL_OPTIONS = [15, 30, 45, 60]
DEFAULT_INTERVAL = 60

BG = "#f4f5f7"
CARD_BG = "#ffffff"
TEXT_PRIMARY = "#1f2430"
TEXT_SECONDARY = "#6b7280"
ACCENT = "#2563eb"
ACCENT_DARK = "#1d4ed8"
HIT_COLOR = "#16a34a"
MISS_COLOR = "#dc2626"
NEUTRAL_BTN_BG = "#e5e7eb"
NEUTRAL_BTN_FG = "#374151"
DISABLED_FG = "#9ca3af"


def data_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)


STATS_PATH = os.path.join(data_dir(), "stats.json")


def today_key():
    return datetime.now().strftime("%Y-%m-%d")


def load_stats():
    if os.path.exists(STATS_PATH):
        try:
            with open(STATS_PATH, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}
    data.setdefault("daily", {})
    data.setdefault("all_time", {"hits": 0, "misses": 0})
    settings = data.setdefault("settings", {})
    settings.setdefault("interval_minutes", DEFAULT_INTERVAL)
    settings.setdefault("always_on_top", True)
    settings.setdefault("auto_detect_teams", False)
    return data


def save_stats(stats):
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2)


def beep():
    if winsound:
        try:
            winsound.Beep(880, 200)
            winsound.Beep(1046, 200)
            winsound.Beep(1318, 300)
        except RuntimeError:
            winsound.MessageBeep()


def flat_button(parent, text, command, bg, fg, font_size=11, bold=True, width=10, state="normal"):
    return tk.Button(
        parent, text=text, command=command, bg=bg, fg=fg,
        activebackground=bg, activeforeground=fg,
        disabledforeground=DISABLED_FG,
        font=("Candara", font_size, "bold" if bold else "normal"),
        relief="flat", bd=0, width=width, padx=6, pady=8,
        cursor="hand2", state=state,
    )


def fetch_latest_release():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
        headers={"User-Agent": "MoveMinder-App"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    tag = data.get("tag_name", "").lstrip("vV")
    download_url = None
    asset_name = None
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.lower().endswith(".exe"):
            download_url = asset.get("browser_download_url")
            asset_name = name
            break
    return tag, download_url, asset_name


def parse_version(v):
    parts = []
    for p in v.split("."):
        digits = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(latest, current):
    return parse_version(latest) > parse_version(current)


def teams_mic_active():
    if winreg is None:
        return False
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as key:
            return _scan_for_teams_mic(key, base, 0)
    except OSError:
        return False


def _scan_for_teams_mic(key, path, depth):
    if depth > 3:
        return False
    i = 0
    while True:
        try:
            subname = winreg.EnumKey(key, i)
        except OSError:
            break
        i += 1
        full_path = f"{path}\\{subname}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, full_path) as subkey:
                if "teams" in subname.lower():
                    try:
                        stop_time, _ = winreg.QueryValueEx(subkey, "LastUsedTimeStop")
                        if stop_time == 0:
                            return True
                    except OSError:
                        pass
                if _scan_for_teams_mic(subkey, full_path, depth + 1):
                    return True
        except OSError:
            continue
    return False


class MoveMinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Move Minder")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        try:
            self.root.iconbitmap(default=resource_path("icon.ico"))
        except tk.TclError:
            pass

        self.stats = load_stats()
        self.state = "stopped"  # stopped | running | reminder_active
        self.next_fire = None
        self.banner = None
        self.active_interval = None
        self.meeting_active = False
        self.pending_update_url = None
        self.pending_update_name = None
        self.current_day = today_key()

        self.root.attributes("-topmost", self.stats["settings"].get("always_on_top", True))

        self.card = tk.Frame(root, bg=CARD_BG, padx=24, pady=20)
        self.card.pack(padx=14, pady=14)

        self.main_frame = tk.Frame(self.card, bg=CARD_BG)
        self.settings_frame = tk.Frame(self.card, bg=CARD_BG)

        self.build_main_view()
        self.build_settings_view()

        self.main_frame.pack()

        self.update_stats_label()
        self.tick()

    # ---------- main view ----------

    def build_main_view(self):
        parent = self.main_frame

        header = tk.Frame(parent, bg=CARD_BG)
        header.pack(fill="x")
        tk.Label(
            header, text="MOVE MINDER", font=("Candara", 11, "bold"),
            bg=CARD_BG, fg=ACCENT,
        ).pack(side="left")
        self.gear_icon = tk.PhotoImage(file=resource_path("gear.png"))
        tk.Button(
            header, image=self.gear_icon, command=self.show_settings, bg=CARD_BG,
            activebackground=CARD_BG, relief="flat", bd=0, cursor="hand2",
        ).pack(side="right")

        self.clock_label = tk.Label(
            parent, font=("Candara", 34, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY,
        )
        self.clock_label.pack(pady=(4, 2))

        self.countdown_label = tk.Label(
            parent, font=("Candara", 12), bg=CARD_BG, fg=TEXT_SECONDARY,
        )
        self.countdown_label.pack(pady=(0, 14))

        interval_wrap = tk.Frame(parent, bg=CARD_BG)
        interval_wrap.pack(fill="x", pady=(0, 14))
        tk.Label(
            interval_wrap, text="INTERVAL", font=("Candara", 8, "bold"),
            bg=CARD_BG, fg=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))

        interval_frame = tk.Frame(interval_wrap, bg=CARD_BG)
        interval_frame.pack()
        self.interval_var = tk.IntVar(
            value=self.stats["settings"].get("interval_minutes", DEFAULT_INTERVAL)
        )
        self.interval_buttons = {}
        for minutes in INTERVAL_OPTIONS:
            btn = tk.Button(
                interval_frame, text=f"{minutes}m", font=("Candara", 9, "bold"),
                relief="flat", bd=0, width=5, padx=2, pady=6, cursor="hand2",
                command=lambda m=minutes: self.select_interval(m),
            )
            btn.pack(side="left", padx=3)
            self.interval_buttons[minutes] = btn
        self.refresh_interval_buttons()

        stats_wrap = tk.Frame(parent, bg=CARD_BG)
        stats_wrap.pack(fill="x", pady=(0, 10))

        self.hits_label = tk.Label(
            stats_wrap, font=("Candara", 10, "bold"), bg=CARD_BG, fg=HIT_COLOR,
        )
        self.hits_label.pack(side="left")

        self.misses_label = tk.Label(
            stats_wrap, font=("Candara", 10, "bold"), bg=CARD_BG, fg=MISS_COLOR,
        )
        self.misses_label.pack(side="left", padx=(14, 0))

        self.all_time_label = tk.Label(
            parent, font=("Candara", 8), bg=CARD_BG, fg=TEXT_SECONDARY,
        )
        self.all_time_label.pack(anchor="w", pady=(0, 10))

        self.meeting_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            parent, text="I'm in a meeting", variable=self.meeting_var,
            command=self.on_meeting_checkbox, bg=CARD_BG, fg=TEXT_PRIMARY,
            activebackground=CARD_BG, activeforeground=TEXT_PRIMARY,
            selectcolor=CARD_BG, font=("Candara", 9), cursor="hand2",
        ).pack(anchor="w", pady=(0, 14))

        btn_frame = tk.Frame(parent, bg=CARD_BG)
        btn_frame.pack(fill="x")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        self.start_btn = flat_button(
            btn_frame, "Start", self.on_start, ACCENT, "#ffffff", width=9,
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.sleep_btn = flat_button(
            btn_frame, "Sleep", self.on_pause, NEUTRAL_BTN_BG, NEUTRAL_BTN_FG,
            width=9, state="disabled",
        )
        self.sleep_btn.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    # ---------- settings view ----------

    def build_settings_view(self):
        parent = self.settings_frame

        header = tk.Frame(parent, bg=CARD_BG)
        header.pack(fill="x", pady=(0, 12))
        tk.Button(
            header, text="← Back", command=self.show_main, bg=CARD_BG, fg=ACCENT,
            activebackground=CARD_BG, activeforeground=ACCENT_DARK, relief="flat", bd=0,
            font=("Candara", 10, "bold"), cursor="hand2",
        ).pack(side="left")
        tk.Label(
            header, text="SETTINGS", font=("Candara", 11, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY,
        ).pack(side="left", padx=(10, 0))

        self._section_label(parent, "PREFERENCES")

        self.always_on_top_var = tk.BooleanVar(
            value=self.stats["settings"].get("always_on_top", True)
        )
        tk.Checkbutton(
            parent, text="Always on top", variable=self.always_on_top_var,
            command=self.on_always_on_top_changed, bg=CARD_BG, fg=TEXT_PRIMARY,
            activebackground=CARD_BG, activeforeground=TEXT_PRIMARY,
            selectcolor=CARD_BG, font=("Candara", 10), cursor="hand2",
        ).pack(anchor="w")

        self.auto_detect_var = tk.BooleanVar(
            value=self.stats["settings"].get("auto_detect_teams", False)
        )
        tk.Checkbutton(
            parent, text="Auto-detect Teams calls (beta)", variable=self.auto_detect_var,
            command=self.on_auto_detect_changed, bg=CARD_BG, fg=TEXT_PRIMARY,
            activebackground=CARD_BG, activeforeground=TEXT_PRIMARY,
            selectcolor=CARD_BG, font=("Candara", 10), cursor="hand2",
        ).pack(anchor="w", pady=(0, 14))

        self._section_label(parent, "LAST 7 DAYS")
        self.week_frame = tk.Frame(parent, bg=CARD_BG)
        self.week_frame.pack(fill="x", pady=(0, 4))

        self.settings_all_time_label = tk.Label(
            parent, font=("Candara", 8), bg=CARD_BG, fg=TEXT_SECONDARY,
        )
        self.settings_all_time_label.pack(anchor="w", pady=(0, 14))

        self._section_label(parent, "UPDATES")
        tk.Label(
            parent, text=f"Version {APP_VERSION}", font=("Candara", 9),
            bg=CARD_BG, fg=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 6))

        self.check_updates_btn = flat_button(
            parent, "Check for Updates", self.on_check_updates,
            NEUTRAL_BTN_BG, NEUTRAL_BTN_FG, font_size=9, width=18,
        )
        self.check_updates_btn.pack(anchor="w")

        self.update_status_label = tk.Label(
            parent, text="", font=("Candara", 9), bg=CARD_BG, fg=TEXT_SECONDARY, wraplength=260,
            justify="left",
        )
        self.update_status_label.pack(anchor="w", pady=(6, 0))

        self.download_btn = flat_button(
            parent, "Download & Restart", self.on_download_update,
            ACCENT, "#ffffff", font_size=9, width=18,
        )

    def _section_label(self, parent, text):
        tk.Label(
            parent, text=text, font=("Candara", 8, "bold"), bg=CARD_BG, fg=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))

    def show_settings(self):
        self.main_frame.pack_forget()
        self.refresh_week_dashboard()
        self.settings_frame.pack()

    def show_main(self):
        self.settings_frame.pack_forget()
        self.main_frame.pack()

    def refresh_week_dashboard(self):
        for widget in self.week_frame.winfo_children():
            widget.destroy()

        today = datetime.now().date()
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            key = day.strftime("%Y-%m-%d")
            entry = self.stats["daily"].get(key, {"hits": 0, "misses": 0})
            row = tk.Frame(self.week_frame, bg=CARD_BG)
            row.pack(fill="x", pady=1)
            tk.Label(
                row, text=day.strftime("%a %m/%d"), font=("Candara", 9),
                bg=CARD_BG, fg=TEXT_PRIMARY, width=10, anchor="w",
            ).pack(side="left")
            tk.Label(
                row, text=f"● {entry['hits']}", font=("Candara", 9, "bold"),
                bg=CARD_BG, fg=HIT_COLOR, width=6, anchor="w",
            ).pack(side="left")
            tk.Label(
                row, text=f"● {entry['misses']}", font=("Candara", 9, "bold"),
                bg=CARD_BG, fg=MISS_COLOR, width=6, anchor="w",
            ).pack(side="left")

        all_time = self.stats["all_time"]
        self.settings_all_time_label.config(
            text=f"All-time: {all_time['hits']} hit / {all_time['misses']} miss"
        )

    # ---------- settings actions ----------

    def on_always_on_top_changed(self):
        value = self.always_on_top_var.get()
        self.stats["settings"]["always_on_top"] = value
        save_stats(self.stats)
        self.root.attributes("-topmost", value)

    def on_auto_detect_changed(self):
        self.stats["settings"]["auto_detect_teams"] = self.auto_detect_var.get()
        save_stats(self.stats)

    def on_check_updates(self):
        self.check_updates_btn.config(state="disabled")
        self.download_btn.pack_forget()
        self.update_status_label.config(text="Checking...", fg=TEXT_SECONDARY)
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self):
        try:
            tag, url, asset_name = fetch_latest_release()
        except Exception:
            self.root.after(0, self._check_updates_failed)
            return
        self.root.after(0, self._check_updates_done, tag, url, asset_name)

    def _check_updates_failed(self):
        self.check_updates_btn.config(state="normal")
        self.update_status_label.config(
            text="Couldn't check for updates. Try again later.", fg=MISS_COLOR
        )

    def _check_updates_done(self, tag, url, asset_name):
        self.check_updates_btn.config(state="normal")
        if not tag:
            self.update_status_label.config(
                text="Couldn't check for updates. Try again later.", fg=MISS_COLOR
            )
            return
        if is_newer(tag, APP_VERSION):
            if getattr(sys, "frozen", False) and url and asset_name:
                self.pending_update_url = url
                self.pending_update_name = asset_name
                self.update_status_label.config(
                    text=f"Update available: v{tag}", fg=ACCENT
                )
                self.download_btn.pack(anchor="w", pady=(6, 0))
            else:
                self.update_status_label.config(
                    text=f"Update available: v{tag} — run 'git pull' to get it "
                         "(auto-update only works in the packaged .exe).",
                    fg=ACCENT,
                )
        else:
            self.update_status_label.config(
                text=f"You're up to date (v{APP_VERSION}).", fg=HIT_COLOR
            )

    def on_download_update(self):
        if not self.pending_update_url or not self.pending_update_name:
            return
        self.download_btn.config(state="disabled")
        self.check_updates_btn.config(state="disabled")
        self.update_status_label.config(text="Downloading update...", fg=TEXT_SECONDARY)
        threading.Thread(
            target=self._download_update_worker,
            args=(self.pending_update_url, self.pending_update_name),
            daemon=True,
        ).start()

    def _download_update_worker(self, url, asset_name):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MoveMinder-App"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
            new_path = os.path.join(data_dir(), f"_update_{asset_name}")
            with open(new_path, "wb") as f:
                f.write(content)
        except Exception:
            self.root.after(0, self._download_update_failed)
            return
        self.root.after(0, self._download_update_done, new_path, asset_name)

    def _download_update_failed(self):
        self.download_btn.config(state="normal")
        self.check_updates_btn.config(state="normal")
        self.update_status_label.config(text="Download failed. Try again.", fg=MISS_COLOR)

    def _download_update_done(self, new_path, asset_name):
        self.update_status_label.config(text="Restarting...", fg=TEXT_SECONDARY)
        self.launch_updater_and_exit(new_path, asset_name)

    def launch_updater_and_exit(self, new_path, target_name):
        # target_name comes from the release asset's own filename, not a hardcoded
        # constant, so this keeps working even if the exe gets renamed again later.
        old_path = sys.executable
        target_path = os.path.join(data_dir(), target_name)
        bat_path = os.path.join(data_dir(), "_moveminder_update.bat")
        pid = os.getpid()
        cleanup_old = (
            f'if exist "{old_path}" del "{old_path}"\r\n' if old_path != target_path else ""
        )
        bat_content = (
            "@echo off\r\n"
            ":waitloop\r\n"
            f'tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL\r\n'
            'if "%ERRORLEVEL%"=="0" (\r\n'
            "    timeout /t 1 /nobreak >nul\r\n"
            "    goto waitloop\r\n"
            ")\r\n"
            f'move /y "{new_path}" "{target_path}" >nul\r\n'
            f"{cleanup_old}"
            f'start "" "{target_path}"\r\n'
            'del "%~f0"\r\n'
        )
        with open(bat_path, "w") as f:
            f.write(bat_content)
        subprocess.Popen(
            ["cmd", "/c", bat_path],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
        save_stats(self.stats)
        self.root.destroy()
        os._exit(0)

    # ---------- interval ----------

    def select_interval(self, minutes):
        if self.state != "stopped":
            return
        self.interval_var.set(minutes)
        self.stats["settings"]["interval_minutes"] = minutes
        save_stats(self.stats)
        self.refresh_interval_buttons()

    def refresh_interval_buttons(self):
        current = self.interval_var.get()
        locked = self.state != "stopped"
        for minutes, btn in self.interval_buttons.items():
            selected = minutes == current
            bg = ACCENT if selected else NEUTRAL_BTN_BG
            fg = "#ffffff" if selected else NEUTRAL_BTN_FG
            btn.config(
                bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                state="disabled" if locked else "normal",
                disabledforeground=fg if selected else DISABLED_FG,
            )

    # ---------- meeting awareness ----------

    def on_meeting_checkbox(self):
        self.set_meeting_active(self.meeting_var.get())

    def set_meeting_active(self, active):
        if active == self.meeting_active:
            return
        self.meeting_active = active
        self.meeting_var.set(active)
        if active:
            if self.state == "reminder_active" and self.banner is not None:
                self.close_banner()
        else:
            if self.state == "running" and self.next_fire is not None and datetime.now() >= self.next_fire:
                self.fire_reminder()

    # ---------- start / pause ----------

    def on_start(self):
        self.state = "running"
        self.active_interval = timedelta(minutes=self.interval_var.get())
        self.next_fire = datetime.now() + self.active_interval
        self.start_btn.config(state="disabled")
        self.sleep_btn.config(state="normal")
        self.refresh_interval_buttons()

    def on_pause(self):
        if self.state == "reminder_active" and self.banner is not None:
            self.log_result("misses")
            self.close_banner()
        self.state = "stopped"
        self.next_fire = None
        self.start_btn.config(state="normal")
        self.sleep_btn.config(state="disabled")
        self.refresh_interval_buttons()

    # ---------- stats ----------

    def log_result(self, kind):
        day = today_key()
        self.stats["daily"].setdefault(day, {"hits": 0, "misses": 0})
        self.stats["daily"][day][kind] += 1
        self.stats["all_time"][kind] += 1
        save_stats(self.stats)
        self.update_stats_label()

    def update_stats_label(self):
        day = today_key()
        today = self.stats["daily"].get(day, {"hits": 0, "misses": 0})
        all_time = self.stats["all_time"]
        self.hits_label.config(text=f"● {today['hits']} today")
        self.misses_label.config(text=f"● {today['misses']} today")
        self.all_time_label.config(
            text=f"All-time: {all_time['hits']} hit / {all_time['misses']} miss"
        )

    # ---------- main loop ----------

    def tick(self):
        self.clock_label.config(text=datetime.now().strftime("%H:%M:%S"))

        day = today_key()
        if day != self.current_day:
            self.current_day = day
            self.update_stats_label()

        if self.auto_detect_var.get():
            desired = teams_mic_active()
            if desired != self.meeting_active:
                self.set_meeting_active(desired)

        if self.state == "running":
            if self.meeting_active:
                self.countdown_label.config(text="In a meeting — reminder paused")
            else:
                remaining = self.next_fire - datetime.now()
                if remaining.total_seconds() <= 0:
                    self.fire_reminder()
                else:
                    mins, secs = divmod(int(remaining.total_seconds()), 60)
                    self.countdown_label.config(text=f"Next squats in {mins:02d}:{secs:02d}")
        elif self.state == "reminder_active":
            remaining = self.next_fire - datetime.now()
            if remaining.total_seconds() <= 0:
                self.log_result("misses")
                self.close_banner()
                self.fire_reminder()
            else:
                self.countdown_label.config(text="Reminder active — respond on the banner!")
        else:
            self.countdown_label.config(text="Stopped")

        self.root.after(1000, self.tick)

    def fire_reminder(self):
        self.state = "reminder_active"
        self.next_fire = datetime.now() + self.active_interval
        beep()
        self.open_banner()

    def open_banner(self):
        self.banner = tk.Toplevel(self.root)
        self.banner.title("Squat time!")
        self.banner.configure(bg=MISS_COLOR)
        self.banner.attributes("-topmost", True)
        self.banner.resizable(False, False)
        self.banner.protocol("WM_DELETE_WINDOW", lambda: None)
        try:
            self.banner.iconbitmap(default=resource_path("icon.ico"))
        except tk.TclError:
            pass

        screen_w = self.banner.winfo_screenwidth()
        screen_h = self.banner.winfo_screenheight()
        w, h = 440, 230
        x, y = (screen_w - w) // 2, (screen_h - h) // 2
        self.banner.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(
            self.banner, text="10 AIR SQUATS!", font=("Candara", 24, "bold"),
            bg=MISS_COLOR, fg="#ffffff",
        ).pack(pady=(28, 8))
        tk.Label(
            self.banner, text="Get up and knock them out.", font=("Candara", 11),
            bg=MISS_COLOR, fg="#ffe4e4",
        ).pack(pady=(0, 22))

        btn_frame = tk.Frame(self.banner, bg=MISS_COLOR)
        btn_frame.pack()

        flat_button(
            btn_frame, "Doing it", self.on_doing_it, "#ffffff", HIT_COLOR, width=12,
        ).grid(row=0, column=0, padx=10)

        flat_button(
            btn_frame, "Skip", self.on_banner_skip, "#7f1d1d", "#ffffff", width=12,
        ).grid(row=0, column=1, padx=10)

        self.banner.lift()
        self.banner.focus_force()

    def close_banner(self):
        if self.banner is not None:
            self.banner.destroy()
            self.banner = None
        if self.state == "reminder_active":
            self.state = "running"

    def on_doing_it(self):
        self.log_result("hits")
        self.close_banner()

    def on_banner_skip(self):
        self.log_result("misses")
        self.close_banner()

    def on_close(self):
        save_stats(self.stats)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MoveMinderApp(root)
    root.mainloop()

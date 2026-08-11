import json
import os
import random
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from datetime import datetime, timedelta
from tkinter import messagebox

try:
    import winsound
except ImportError:
    winsound = None

try:
    import winreg
except ImportError:
    winreg = None

APP_VERSION = "2.4.2"
GITHUB_REPO = "mspahn303/move-minder"

INTERVAL_OPTIONS = [15, 30, 45, 60]
DEFAULT_INTERVAL = 60

# "baseline_reps" is the reference rep count each exercise's XP value assumes;
# actual assigned reps (5-20, randomized per session) scale XP proportionally.
EXERCISES = [
    {"id": "squats", "name": "Squats", "baseline_reps": 10, "difficulty": "easy"},
    {"id": "pushups", "name": "Push-ups", "baseline_reps": 10, "difficulty": "medium"},
    {"id": "situps", "name": "Sit-ups", "baseline_reps": 10, "difficulty": "easy"},
    {"id": "burpees", "name": "Burpees", "baseline_reps": 10, "difficulty": "hard"},
    {"id": "jumping_jacks", "name": "Jumping Jacks", "baseline_reps": 10, "difficulty": "easy"},
]

# Single-exercise sessions pick a rep count from this list. Combo (2-exercise)
# sessions are always split evenly at the minimum since min-per-exercise * 2
# already equals the max -- there's no room left for any other split.
SESSION_REP_CHOICES = [10, 15, 20]
SESSION_COMBO_REPS_EACH = 10

# Base XP per difficulty tier, and how much it decays per level toward a floor
# (as a fraction of base). Easy decays fastest, hard barely decays -- the pull
# toward harder exercises as you level up.
XP_CURVE = {
    "easy": {"base": 10, "decay_per_level": 0.08, "floor_fraction": 0.2},
    "medium": {"base": 15, "decay_per_level": 0.04, "floor_fraction": 0.4},
    "hard": {"base": 25, "decay_per_level": 0.015, "floor_fraction": 0.7},
}

LEVEL_XP_BASE = 100
LEVEL_XP_EXPONENT = 1.3
XP_BAR_WIDTH = 248


def exercise_by_id(ex_id):
    for ex in EXERCISES:
        if ex["id"] == ex_id:
            return ex
    return EXERCISES[0]


def enabled_exercise_ids(stats):
    enabled = stats["settings"].get("exercise_enabled", {})
    ids = [ex["id"] for ex in EXERCISES if enabled.get(ex["id"], True)]
    return ids if ids else [ex["id"] for ex in EXERCISES]


def xp_required_for_level(level):
    return round(LEVEL_XP_BASE * (level ** LEVEL_XP_EXPONENT))


def level_from_total_xp(total_xp):
    level = 1
    remaining = total_xp
    while remaining >= xp_required_for_level(level):
        remaining -= xp_required_for_level(level)
        level += 1
    return level, remaining, xp_required_for_level(level)


def xp_value(exercise, level, reps):
    curve = XP_CURVE[exercise["difficulty"]]
    multiplier = max(curve["floor_fraction"], 1 - curve["decay_per_level"] * (level - 1))
    return curve["base"] * multiplier * (reps / exercise["baseline_reps"])


def session_xp(session, level):
    return round(sum(xp_value(exercise_by_id(ex_id), level, reps) for ex_id, reps in session))


def build_session(stats, previous_session):
    ids = enabled_exercise_ids(stats)
    size = random.choice([1, 2]) if len(ids) >= 2 else 1

    prev_ids = {ex_id for ex_id, _ in (previous_session or [])}
    pool = [i for i in ids if i not in prev_ids]
    if len(pool) < size:
        pool = ids
    chosen = random.sample(pool, size) if len(pool) >= size else random.sample(ids, size)

    if size == 1:
        reps_list = [random.choice(SESSION_REP_CHOICES)]
    else:
        reps_list = [SESSION_COMBO_REPS_EACH, SESSION_COMBO_REPS_EACH]

    return list(zip(chosen, reps_list))

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
    all_time = data.setdefault("all_time", {"hits": 0, "misses": 0})
    all_time.setdefault("by_exercise", {})
    settings = data.setdefault("settings", {})
    settings.setdefault("interval_minutes", DEFAULT_INTERVAL)
    settings.setdefault("always_on_top", True)
    settings.setdefault("auto_detect_teams", False)
    settings.setdefault("show_meeting_checkbox", True)
    exercise_enabled = settings.setdefault("exercise_enabled", {})
    for ex in EXERCISES:
        exercise_enabled.setdefault(ex["id"], True)
    gamification = data.setdefault("gamification", {})
    gamification.setdefault("total_xp", 0)
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
        self.current_session = []
        self.anim_images = self.load_anim_images()
        self.banner_anim_rows = []
        self.banner_anim_index = 0
        self.banner_anim_after_id = None
        self.pre_impromptu_state = None

        self.root.attributes("-topmost", self.stats["settings"].get("always_on_top", True))

        self.card = tk.Frame(root, bg=CARD_BG, padx=24, pady=20)
        self.card.pack(padx=14, pady=14)

        self.main_frame = tk.Frame(self.card, bg=CARD_BG)
        self.settings_frame = tk.Frame(self.card, bg=CARD_BG)

        self.build_main_view()
        self.build_settings_view()

        self.main_frame.pack()

        self.update_stats_label()
        self.update_xp_display()
        self.tick()

    def load_anim_images(self):
        images = {}
        for ex in EXERCISES:
            frames = []
            for i in (0, 1):
                try:
                    frames.append(tk.PhotoImage(file=resource_path(f"anim_{ex['id']}_{i}.png")))
                except tk.TclError:
                    frames.append(None)
            images[ex["id"]] = frames
        return images

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

        level_wrap = tk.Frame(parent, bg=CARD_BG)
        level_wrap.pack(fill="x", pady=(0, 10))

        self.level_label = tk.Label(
            level_wrap, font=("Candara", 10, "bold"), bg=CARD_BG, fg=ACCENT,
        )
        self.level_label.pack(anchor="w")

        self.xp_bar_bg = tk.Frame(level_wrap, bg=NEUTRAL_BTN_BG, height=8, width=XP_BAR_WIDTH)
        self.xp_bar_bg.pack(anchor="w", pady=(4, 2))
        self.xp_bar_bg.pack_propagate(False)
        self.xp_bar_fill = tk.Frame(self.xp_bar_bg, bg=ACCENT, height=8, width=0)
        self.xp_bar_fill.place(x=0, y=0)

        self.xp_label = tk.Label(
            level_wrap, font=("Candara", 8), bg=CARD_BG, fg=TEXT_SECONDARY,
        )
        self.xp_label.pack(anchor="w")

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
        self.meeting_checkbox = tk.Checkbutton(
            parent, text="I'm in a meeting", variable=self.meeting_var,
            command=self.on_meeting_checkbox, bg=CARD_BG, fg=TEXT_PRIMARY,
            activebackground=CARD_BG, activeforeground=TEXT_PRIMARY,
            selectcolor=CARD_BG, font=("Candara", 9), cursor="hand2",
        )
        if self.stats["settings"].get("show_meeting_checkbox", True):
            self.meeting_checkbox.pack(anchor="w", pady=(0, 14))

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

        self.impromptu_btn = flat_button(
            parent, "Impromptu Session", self.on_impromptu_session,
            NEUTRAL_BTN_BG, NEUTRAL_BTN_FG, font_size=9, width=20,
        )
        self.impromptu_btn.pack(fill="x", pady=(8, 0))

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
        ).pack(anchor="w")

        self.show_meeting_checkbox_var = tk.BooleanVar(
            value=self.stats["settings"].get("show_meeting_checkbox", True)
        )
        tk.Checkbutton(
            parent, text="Show \"I'm in a meeting\" checkbox on main window",
            variable=self.show_meeting_checkbox_var, command=self.on_show_meeting_checkbox_changed,
            bg=CARD_BG, fg=TEXT_PRIMARY, activebackground=CARD_BG, activeforeground=TEXT_PRIMARY,
            selectcolor=CARD_BG, font=("Candara", 10), cursor="hand2",
        ).pack(anchor="w", pady=(0, 14))

        self._section_label(parent, "EXERCISES")
        self.exercise_vars = {}
        exercise_enabled = self.stats["settings"].get("exercise_enabled", {})
        for ex in EXERCISES:
            var = tk.BooleanVar(value=exercise_enabled.get(ex["id"], True))
            self.exercise_vars[ex["id"]] = var
            tk.Checkbutton(
                parent, text=ex["name"], variable=var,
                command=lambda ex_id=ex["id"]: self.on_exercise_toggle(ex_id),
                bg=CARD_BG, fg=TEXT_PRIMARY, activebackground=CARD_BG,
                activeforeground=TEXT_PRIMARY, selectcolor=CARD_BG,
                font=("Candara", 10), cursor="hand2",
            ).pack(anchor="w")

        self.exercise_warning_label = tk.Label(
            parent, text="", font=("Candara", 8), bg=CARD_BG, fg=MISS_COLOR,
        )
        self.exercise_warning_label.pack(anchor="w", pady=(2, 14))

        self._section_label(parent, "LAST 7 DAYS")
        self.week_frame = tk.Frame(parent, bg=CARD_BG)
        self.week_frame.pack(fill="x", pady=(0, 4))

        self.settings_all_time_label = tk.Label(
            parent, font=("Candara", 8), bg=CARD_BG, fg=TEXT_SECONDARY,
        )
        self.settings_all_time_label.pack(anchor="w", pady=(0, 14))

        self._section_label(parent, "DATA")
        reset_frame = tk.Frame(parent, bg=CARD_BG)
        reset_frame.pack(fill="x", pady=(0, 4))

        flat_button(
            reset_frame, "Reset Daily Stats", self.on_reset_daily_stats,
            NEUTRAL_BTN_BG, NEUTRAL_BTN_FG, font_size=9, width=16,
        ).grid(row=0, column=0, padx=(0, 6))

        flat_button(
            reset_frame, "Reset All Stats", self.on_reset_all_stats,
            NEUTRAL_BTN_BG, MISS_COLOR, font_size=9, width=16,
        ).grid(row=0, column=1, padx=(6, 0))

        self.reset_status_label = tk.Label(
            parent, text="", font=("Candara", 8), bg=CARD_BG, fg=TEXT_SECONDARY,
        )
        self.reset_status_label.pack(anchor="w", pady=(6, 14))

        self._section_label(parent, "UPDATES")
        tk.Label(
            parent, text=f"Current: v{APP_VERSION}", font=("Candara", 9),
            bg=CARD_BG, fg=TEXT_SECONDARY,
        ).pack(anchor="w")

        self.update_status_label = tk.Label(
            parent, text="Latest: checking...", font=("Candara", 9),
            bg=CARD_BG, fg=TEXT_SECONDARY, wraplength=260, justify="left",
        )
        self.update_status_label.pack(anchor="w", pady=(0, 6))

        self.download_btn = flat_button(
            parent, "Update", self.on_download_update,
            ACCENT, "#ffffff", font_size=9, width=18,
        )

        self.check_updates_btn = flat_button(
            parent, "Check Again", self.on_check_updates,
            NEUTRAL_BTN_BG, NEUTRAL_BTN_FG, font_size=8, width=12,
        )
        self.check_updates_btn.pack(anchor="w", pady=(6, 0))

    def _section_label(self, parent, text):
        tk.Label(
            parent, text=text, font=("Candara", 8, "bold"), bg=CARD_BG, fg=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))

    def show_settings(self):
        self.main_frame.pack_forget()
        self.refresh_week_dashboard()
        self.settings_frame.pack()
        self.on_check_updates()

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

    def on_show_meeting_checkbox_changed(self):
        value = self.show_meeting_checkbox_var.get()
        self.stats["settings"]["show_meeting_checkbox"] = value
        save_stats(self.stats)
        if value:
            self.meeting_checkbox.pack(anchor="w", pady=(0, 14))
        else:
            self.meeting_checkbox.pack_forget()

    def on_reset_daily_stats(self):
        if not messagebox.askyesno(
            "Reset Daily Stats",
            "Clear all day-by-day history? All-time totals and your level/XP "
            "are not affected.",
            parent=self.settings_frame.winfo_toplevel(),
        ):
            return
        self.stats["daily"] = {}
        save_stats(self.stats)
        self.update_stats_label()
        self.refresh_week_dashboard()
        self.reset_status_label.config(text="Daily stats cleared.", fg=HIT_COLOR)

    def on_reset_all_stats(self):
        if not messagebox.askyesno(
            "Reset All Stats",
            "Wipe daily history, all-time totals, and your level/XP back to "
            "zero? This can't be undone.",
            parent=self.settings_frame.winfo_toplevel(),
        ):
            return
        self.stats["daily"] = {}
        self.stats["all_time"] = {"hits": 0, "misses": 0, "by_exercise": {}}
        self.stats["gamification"]["total_xp"] = 0
        save_stats(self.stats)
        self.update_stats_label()
        self.update_xp_display()
        self.refresh_week_dashboard()
        self.reset_status_label.config(text="All stats reset.", fg=HIT_COLOR)

    def on_exercise_toggle(self, ex_id):
        still_enabled = [eid for eid, var in self.exercise_vars.items() if var.get()]
        if not still_enabled:
            self.exercise_vars[ex_id].set(True)
            self.exercise_warning_label.config(text="At least one exercise must stay enabled.")
            return
        self.exercise_warning_label.config(text="")
        self.stats["settings"]["exercise_enabled"][ex_id] = self.exercise_vars[ex_id].get()
        save_stats(self.stats)

    def on_check_updates(self):
        self.check_updates_btn.config(state="disabled")
        self.download_btn.pack_forget()
        self.update_status_label.config(text="Latest: checking...", fg=TEXT_SECONDARY)
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
            text="Latest: couldn't check for updates.", fg=MISS_COLOR
        )

    def _check_updates_done(self, tag, url, asset_name):
        self.check_updates_btn.config(state="normal")
        if not tag:
            self.update_status_label.config(
                text="Latest: couldn't check for updates.", fg=MISS_COLOR
            )
            return
        if is_newer(tag, APP_VERSION):
            if getattr(sys, "frozen", False) and url and asset_name:
                self.pending_update_url = url
                self.pending_update_name = asset_name
                self.update_status_label.config(text=f"Latest: v{tag}", fg=ACCENT)
                self.download_btn.pack(anchor="w", pady=(6, 0), before=self.check_updates_btn)
            else:
                self.update_status_label.config(
                    text=f"Latest: v{tag} — run 'git pull' to get it "
                         "(auto-update only works in the packaged .exe).",
                    fg=ACCENT,
                )
        else:
            self.update_status_label.config(text=f"Latest: v{tag} (up to date)", fg=HIT_COLOR)

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
        day_entry = self.stats["daily"].setdefault(day, {"hits": 0, "misses": 0})
        day_entry.setdefault("by_exercise", {})
        day_entry[kind] += 1

        session = self.current_session or [(EXERCISES[0]["id"], EXERCISES[0]["baseline_reps"])]
        for ex_id, reps in session:
            day_ex = day_entry["by_exercise"].setdefault(ex_id, {"hits": 0, "misses": 0})
            day_ex[kind] += 1
            all_time_ex = self.stats["all_time"]["by_exercise"].setdefault(
                ex_id, {"hits": 0, "misses": 0}
            )
            all_time_ex[kind] += 1

        self.stats["all_time"][kind] += 1

        if kind == "hits":
            level_before, _, _ = level_from_total_xp(self.stats["gamification"]["total_xp"])
            gained = session_xp(session, level_before)
            self.stats["gamification"]["total_xp"] += gained
            level_after, _, _ = level_from_total_xp(self.stats["gamification"]["total_xp"])
            self.update_xp_display()
            if level_after > level_before:
                self.show_level_up_popup(level_after)

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

    def update_xp_display(self):
        level, xp_into_level, xp_needed = level_from_total_xp(
            self.stats["gamification"]["total_xp"]
        )
        self.level_label.config(text=f"Level {level}")
        fraction = min(1.0, xp_into_level / xp_needed) if xp_needed else 1.0
        self.xp_bar_fill.config(width=int(XP_BAR_WIDTH * fraction))
        self.xp_label.config(text=f"{xp_into_level} / {xp_needed} XP")

    def show_level_up_popup(self, level):
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.configure(bg=HIT_COLOR)
        popup.attributes("-topmost", True)

        w, h = 260, 90
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x, y = (screen_w - w) // 2, (screen_h - h) // 2
        popup.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(
            popup, text="LEVEL UP!", font=("Candara", 16, "bold"),
            bg=HIT_COLOR, fg="#ffffff",
        ).pack(pady=(16, 2))
        tk.Label(
            popup, text=f"You're now Level {level}", font=("Candara", 11),
            bg=HIT_COLOR, fg="#e7ffe9",
        ).pack()

        popup.after(2200, popup.destroy)

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
                    self.countdown_label.config(text=f"Next reminder in {mins:02d}:{secs:02d}")
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
        self.current_session = build_session(self.stats, self.current_session)
        beep()
        self.open_banner()

    def on_impromptu_session(self):
        if self.state == "reminder_active":
            return
        self.pre_impromptu_state = self.state
        interval = self.active_interval or timedelta(minutes=self.interval_var.get())
        self.active_interval = interval
        self.next_fire = datetime.now() + interval
        self.state = "reminder_active"
        self.current_session = build_session(self.stats, self.current_session)
        beep()
        self.open_banner()

    def open_banner(self):
        self.impromptu_btn.config(state="disabled")
        self.refresh_interval_buttons()
        self.banner = tk.Toplevel(self.root)
        self.banner.title("Move time!")
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
        w = 440
        h = 260 + max(0, len(self.current_session) - 1) * 74
        x, y = (screen_w - w) // 2, (screen_h - h) // 2
        self.banner.geometry(f"{w}x{h}+{x}+{y}")

        self.banner_anim_rows = []
        self.banner_anim_index = 0
        for ex_id, reps in self.current_session:
            exercise = exercise_by_id(ex_id)
            row = tk.Frame(self.banner, bg=MISS_COLOR)
            row.pack(pady=(14, 0))
            frames = self.anim_images.get(ex_id)
            img_label = tk.Label(row, bg=MISS_COLOR)
            if frames and frames[0] is not None:
                img_label.config(image=frames[0])
            img_label.pack(side="left", padx=(0, 12))
            tk.Label(
                row, text=f"{reps} {exercise['name'].upper()}!",
                font=("Candara", 22, "bold"), bg=MISS_COLOR, fg="#ffffff",
            ).pack(side="left")
            self.banner_anim_rows.append((img_label, ex_id))
        tk.Label(
            self.banner, text="Get up and knock them out.", font=("Candara", 11),
            bg=MISS_COLOR, fg="#ffe4e4",
        ).pack(pady=(10, 18))

        self.cycle_banner_animation()

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

    def cycle_banner_animation(self):
        self.banner_anim_index = 1 - self.banner_anim_index
        for img_label, ex_id in self.banner_anim_rows:
            frames = self.anim_images.get(ex_id)
            if frames and frames[self.banner_anim_index] is not None:
                img_label.config(image=frames[self.banner_anim_index])
        self.banner_anim_after_id = self.banner.after(400, self.cycle_banner_animation)

    def close_banner(self):
        if self.banner is not None:
            if self.banner_anim_after_id is not None:
                self.banner.after_cancel(self.banner_anim_after_id)
                self.banner_anim_after_id = None
            self.banner.destroy()
            self.banner = None
            self.banner_anim_rows = []
        self.impromptu_btn.config(state="normal")
        if self.state == "reminder_active":
            self.state = self.pre_impromptu_state if self.pre_impromptu_state is not None else "running"
        self.pre_impromptu_state = None
        if self.state == "stopped":
            self.next_fire = None
        self.refresh_interval_buttons()

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

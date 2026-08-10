import json
import os
import sys
import tkinter as tk
from datetime import datetime, timedelta

try:
    import winsound
except ImportError:
    winsound = None

INTERVAL_OPTIONS = [15, 30, 45, 60]
DEFAULT_INTERVAL = 60

BG = "#f4f5f7"
CARD_BG = "#ffffff"
TEXT_PRIMARY = "#1f2430"
TEXT_SECONDARY = "#6b7280"
ACCENT = "#4f46e5"
ACCENT_DARK = "#4338ca"
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
                data.setdefault("daily", {})
                data.setdefault("all_time", {"hits": 0, "misses": 0})
                data.setdefault("settings", {"interval_minutes": DEFAULT_INTERVAL})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "daily": {},
        "all_time": {"hits": 0, "misses": 0},
        "settings": {"interval_minutes": DEFAULT_INTERVAL},
    }


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
        font=("Segoe UI", font_size, "bold" if bold else "normal"),
        relief="flat", bd=0, width=width, padx=6, pady=8,
        cursor="hand2", state=state,
    )


class AirSquatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AirSquat")
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
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

        card = tk.Frame(root, bg=CARD_BG, padx=24, pady=20)
        card.pack(padx=14, pady=14)

        tk.Label(
            card, text="AIRSQUAT", font=("Segoe UI", 11, "bold"),
            bg=CARD_BG, fg=ACCENT,
        ).pack(anchor="w")

        self.clock_label = tk.Label(
            card, font=("Segoe UI", 34, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY,
        )
        self.clock_label.pack(pady=(4, 2))

        self.countdown_label = tk.Label(
            card, font=("Segoe UI", 12), bg=CARD_BG, fg=TEXT_SECONDARY,
        )
        self.countdown_label.pack(pady=(0, 14))

        interval_wrap = tk.Frame(card, bg=CARD_BG)
        interval_wrap.pack(fill="x", pady=(0, 14))
        tk.Label(
            interval_wrap, text="INTERVAL", font=("Segoe UI", 8, "bold"),
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
                interval_frame, text=f"{minutes}m", font=("Segoe UI", 9, "bold"),
                relief="flat", bd=0, width=5, padx=2, pady=6, cursor="hand2",
                command=lambda m=minutes: self.select_interval(m),
            )
            btn.pack(side="left", padx=3)
            self.interval_buttons[minutes] = btn
        self.refresh_interval_buttons()

        stats_wrap = tk.Frame(card, bg=CARD_BG)
        stats_wrap.pack(fill="x", pady=(0, 16))

        self.hits_label = tk.Label(
            stats_wrap, font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=HIT_COLOR,
        )
        self.hits_label.pack(side="left")

        self.misses_label = tk.Label(
            stats_wrap, font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=MISS_COLOR,
        )
        self.misses_label.pack(side="left", padx=(14, 0))

        self.all_time_label = tk.Label(
            card, font=("Segoe UI", 8), bg=CARD_BG, fg=TEXT_SECONDARY,
        )
        self.all_time_label.pack(anchor="w", pady=(0, 14))

        btn_frame = tk.Frame(card, bg=CARD_BG)
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

        self.update_stats_label()
        self.tick()

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

    def tick(self):
        self.clock_label.config(text=datetime.now().strftime("%H:%M:%S"))

        if self.state == "running":
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
            self.banner, text="10 AIR SQUATS!", font=("Segoe UI", 24, "bold"),
            bg=MISS_COLOR, fg="#ffffff",
        ).pack(pady=(28, 8))
        tk.Label(
            self.banner, text="Get up and knock them out.", font=("Segoe UI", 11),
            bg=MISS_COLOR, fg="#ffe4e4",
        ).pack(pady=(0, 22))

        btn_frame = tk.Frame(self.banner, bg=MISS_COLOR)
        btn_frame.pack()

        flat_button(
            btn_frame, "Doing it", self.on_doing_it, "#ffffff", HIT_COLOR, width=12,
        ).grid(row=0, column=0, padx=10)

        flat_button(
            btn_frame, "Sleep", self.on_banner_sleep, "#7f1d1d", "#ffffff", width=12,
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

    def on_banner_sleep(self):
        self.log_result("misses")
        self.close_banner()

    def on_close(self):
        save_stats(self.stats)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AirSquatApp(root)
    root.mainloop()

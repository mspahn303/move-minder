# Move Minder

A tiny Windows app that reminds you to get up and move on a timer, tracks how
often you actually do it, and beeps at you until you do.

> Formerly known as AirSquat — renamed as the app grows beyond just squats.

## Download

Grab the latest `MoveMinder.exe` from the [Releases page](../../releases/latest) —
no install, no Python required. Just download and double-click.

> Windows may show a "Windows protected your PC" SmartScreen warning because
> the app isn't code-signed. Click **More info → Run anyway** to launch it.

## How it works

- Pick a reminder interval: **15, 30, 45, or 60 minutes**.
- Press **Start** to begin the countdown.
- When it hits zero, a banner pops up with a beep showing a randomly generated
  session — one exercise most of the time, sometimes two back-to-back (e.g.
  **10 SQUATS!** + **10 SIT-UPS!**) — picked from Squats, Push-ups, Sit-ups,
  Burpees, and Jumping Jacks, never repeating the same exercise set twice in a
  row. Single-exercise sessions get a random rep count of 10, 15, or 20; combo
  sessions are always split evenly at 10 reps each.
  - **Doing it** — logs a hit for the whole session, awards XP (shown as a
    floating **+XP** on the banner), and restarts the countdown.
  - **Skip** — logs a miss for the whole session, costs XP (shown as a
    floating **−XP**), dismisses the banner, and restarts the countdown.
  - Ignore it completely and it auto-logs as a miss (same XP cost, no
    animation) once the next interval starts.
  - Each exercise in the banner has a small looping animation next to it, so
    you can see the motion instead of just reading the name.
  - While a session is active, the main window shows a short **"Ready?"**
    instead of a long status line, so the window doesn't grow wider.
- **Sleep** on the main window pauses the whole cycle (e.g. overnight) without
  logging a miss.
- **Level & XP bar** on the main window tracks your progress. Harder exercises
  (burpees > push-ups > squats/sit-ups/jumping jacks) are worth more XP to
  begin with, and as you level up, XP value grows further — hard exercises
  grow fastest and plateau highest, so they stay worth doing longest. XP
  required per level keeps rising with no cap, so leveling still naturally
  slows down over time even though rewards never shrink. Skipping or missing
  costs a slice of your current level's required XP (never below zero total).
  Leveling up triggers a brief celebration popup.
- **"I'm in a meeting"** checkbox (optional, see Settings) suppresses
  reminders while checked (no miss logged) — when you uncheck it, any
  reminder that was due fires immediately, then the timer restarts fresh
  from that moment.
- **Impromptu Session** button (below Start/Sleep) fires off a session on
  demand — handy for squeezing one in before a meeting eats your next
  scheduled reminder. Works whether the timer is running or stopped. If it
  was running, the countdown restarts fresh from that moment; if it was
  stopped, it stays stopped afterward. Counts toward stats and XP exactly
  like a normal reminder.
- Hit/miss stats are saved to `stats.json` next to the app and persist across
  restarts and reboots.

> As of v2.6.0, fresh installs default to auto-detect on, the manual meeting
> checkbox off, and 12-hour time. These are defaults only — if you already
> have a `stats.json` from an earlier version, your existing settings are
> left as-is; flip the toggles in Settings if you want the new defaults.

## Settings (⚙)

- **Appearance** — three themes, switch anytime with no restart needed:
  - **Light** — the original look.
  - **Dark** — a dark palette for low-light use.
  - **Nostalgia** — a Windows XP-era homage (Luna blue/beige palette, chunky
    beveled buttons, Tahoma font). Note: Tkinter can't restyle the OS-drawn
    window title bar, so that part stays whatever your actual Windows theme
    renders — the homage applies to the app's own content area.
- **Always on top** — toggle whether the window stays above other windows.
- **24-hour time** — toggle between 24-hour and 12-hour (AM/PM) clock display
  on the main window. Defaults to 12-hour.
- **Auto-detect Teams calls (beta)** — on by default. When enabled, the app
  checks whether Teams currently has your microphone open and automatically
  suppresses reminders during meetings. It's a heuristic (no Teams login or
  API involved), not a guarantee, and it keeps working even if you hide the
  meeting checkbox below.
- **Show "I'm in a meeting" checkbox on main window** — off by default now
  that auto-detect is on by default. Turn on if you want the manual checkbox
  visible too (e.g. for non-Teams calls). Auto-detect keeps running
  regardless of this setting.
- **Exercises** — enable/disable individual exercises from the rotation (at
  least one must stay enabled).
- **Last 7 days** — a day-by-day hit/miss dashboard, plus all-time totals.
- **Reset Daily Stats** — clears the day-by-day history (with a confirmation
  prompt). All-time totals and your level/XP are untouched.
- **Reset All Stats** — wipes daily history, all-time totals, and level/XP
  back to zero (with a confirmation prompt). Can't be undone.
- **Updates** — opening Settings automatically checks this repo's latest
  GitHub Release and shows both your current version and the latest one. If
  a newer version exists and you're running the packaged `.exe`, an
  **Update** button appears — one click downloads it and restarts the app
  automatically. Running from source instead just tells you to `git pull`.
  A small **Check Again** button lets you manually re-check anytime,
  including as a retry if the automatic check couldn't reach GitHub.

## Building from source

Requires Python 3.10+ on Windows.

```bash
pip install pyinstaller pillow
python make_icon.py         # regenerates icon.ico and gear.png
python make_animations.py   # regenerates the exercise animation frames
pyinstaller --onefile --windowed --icon=icon.ico --name MoveMinder ^
  --add-data "icon.ico;." --add-data "gear.png;." ^
  --add-data "anim_squats_0.png;." --add-data "anim_squats_1.png;." ^
  --add-data "anim_pushups_0.png;." --add-data "anim_pushups_1.png;." ^
  --add-data "anim_situps_0.png;." --add-data "anim_situps_1.png;." ^
  --add-data "anim_burpees_0.png;." --add-data "anim_burpees_1.png;." ^
  --add-data "anim_jumping_jacks_0.png;." --add-data "anim_jumping_jacks_1.png;." ^
  --add-binary "C:\Windows\System32\msvcp140.dll;." ^
  --add-binary "C:\Windows\System32\vcruntime140_1.dll;." ^
  move_minder.py
```

The built exe will be in `dist/MoveMinder.exe`.

> The two `--add-binary` flags matter: PyInstaller's automatic dependency
> scan doesn't reliably pick up `msvcp140.dll` / `vcruntime140_1.dll`, even
> though `python3xx.dll` needs them. Without bundling them explicitly, the
> exe only works on machines that happen to already have the Visual C++
> Redistributable installed — anywhere else it fails with "Failed to load
> Python DLL ... LoadLibrary: The specified module could not be found."

Pushing a version tag (e.g. `v2.0.0`) triggers a GitHub Actions workflow that
builds the exe and attaches it to a new GitHub Release automatically. When you
cut a release, bump `APP_VERSION` in `move_minder.py` to match the tag first —
that's what powers the in-app "Check for Updates" comparison.

## License

MIT — see [LICENSE](LICENSE).

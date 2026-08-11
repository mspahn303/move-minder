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
  - **Doing it** — logs a hit for the whole session, awards XP, and restarts
    the countdown.
  - **Skip** — logs a miss for the whole session, dismisses the banner, and
    restarts the countdown.
  - Ignore it completely and it auto-logs as a miss once the next interval starts.
  - Each exercise in the banner has a small looping animation next to it, so
    you can see the motion instead of just reading the name.
- **Sleep** on the main window pauses the whole cycle (e.g. overnight) without
  logging a miss.
- **Level & XP bar** on the main window tracks your progress. Harder exercises
  (burpees > push-ups > squats/sit-ups/jumping jacks) are worth more XP, and as
  you level up, easy exercises' XP value decays toward a floor much faster than
  hard ones do — so the higher your level, the more the game nudges you toward
  tougher exercises to keep progressing at a good pace. Leveling up triggers a
  brief celebration popup.
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

## Settings (⚙)

- **Always on top** — toggle whether the window stays above other windows.
- **Auto-detect Teams calls (beta)** — when enabled, the app checks whether
  Teams currently has your microphone open and automatically suppresses
  reminders during meetings. It's a heuristic (no Teams login or API
  involved), not a guarantee, and it keeps working even if you hide the
  meeting checkbox below.
- **Show "I'm in a meeting" checkbox on main window** — turn off if you rely
  on auto-detect and don't want the manual checkbox cluttering the main
  window. Auto-detect keeps running regardless of this setting.
- **Exercises** — enable/disable individual exercises from the rotation (at
  least one must stay enabled).
- **Last 7 days** — a day-by-day hit/miss dashboard, plus all-time totals.
- **Reset Daily Stats** — clears the day-by-day history (with a confirmation
  prompt). All-time totals and your level/XP are untouched.
- **Reset All Stats** — wipes daily history, all-time totals, and level/XP
  back to zero (with a confirmation prompt). Can't be undone.
- **Check for Updates** — queries this repo's latest GitHub Release. If a newer
  version exists and you're running the packaged `.exe`, one click downloads it
  and restarts the app on the new version automatically. Running from source
  instead just tells you to `git pull`.

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
  move_minder.py
```

The built exe will be in `dist/MoveMinder.exe`.

Pushing a version tag (e.g. `v2.0.0`) triggers a GitHub Actions workflow that
builds the exe and attaches it to a new GitHub Release automatically. When you
cut a release, bump `APP_VERSION` in `move_minder.py` to match the tag first —
that's what powers the in-app "Check for Updates" comparison.

## License

MIT — see [LICENSE](LICENSE).

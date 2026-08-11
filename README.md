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
- When it hits zero, a banner pops up with a beep: **10 AIR SQUATS!**
  - **Doing it** — logs a hit and restarts the countdown.
  - **Skip** — logs a miss, dismisses the banner, restarts the countdown.
  - Ignore it completely and it auto-logs as a miss once the next interval starts.
- **Sleep** on the main window pauses the whole cycle (e.g. overnight) without
  logging a miss.
- **"I'm in a meeting"** checkbox suppresses reminders while checked (no miss
  logged) — when you uncheck it, any reminder that was due fires immediately,
  then the timer restarts fresh from that moment.
- Hit/miss stats are saved to `stats.json` next to the app and persist across
  restarts and reboots.

## Settings (⚙)

- **Always on top** — toggle whether the window stays above other windows.
- **Auto-detect Teams calls (beta)** — when enabled, the app checks whether
  Teams currently has your microphone open and automatically checks/unchecks
  "I'm in a meeting" for you. It's a heuristic (no Teams login or API involved),
  not a guarantee — you can always override it manually, including for non-Teams
  calls.
- **Last 7 days** — a day-by-day hit/miss dashboard, plus all-time totals.
- **Check for Updates** — queries this repo's latest GitHub Release. If a newer
  version exists and you're running the packaged `.exe`, one click downloads it
  and restarts the app on the new version automatically. Running from source
  instead just tells you to `git pull`.

## Building from source

Requires Python 3.10+ on Windows.

```bash
pip install pyinstaller pillow
python make_icon.py   # regenerates icon.ico and gear.png
pyinstaller --onefile --windowed --icon=icon.ico --name MoveMinder --add-data "icon.ico;." --add-data "gear.png;." move_minder.py
```

The built exe will be in `dist/MoveMinder.exe`.

Pushing a version tag (e.g. `v2.0.0`) triggers a GitHub Actions workflow that
builds the exe and attaches it to a new GitHub Release automatically. When you
cut a release, bump `APP_VERSION` in `move_minder.py` to match the tag first —
that's what powers the in-app "Check for Updates" comparison.

## License

MIT — see [LICENSE](LICENSE).

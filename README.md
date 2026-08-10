# AirSquat

A tiny always-on-top Windows app that reminds you to do 10 air squats on a
timer, tracks how often you actually do them, and beeps at you until you do.

## Download

Grab the latest `AirSquat.exe` from the [Releases page](../../releases/latest) —
no install, no Python required. Just download and double-click.

> Windows may show a "Windows protected your PC" SmartScreen warning because
> the app isn't code-signed. Click **More info → Run anyway** to launch it.

## How it works

- Pick a reminder interval: **15, 30, 45, or 60 minutes**.
- Press **Start** to begin the countdown.
- When it hits zero, a banner pops up with a beep: **10 AIR SQUATS!**
  - **Doing it** — logs a hit and restarts the countdown.
  - **Sleep** — logs a miss, dismisses the banner, restarts the countdown.
  - Ignore it completely and it auto-logs as a miss once the next interval starts.
- **Sleep** on the main window pauses the whole cycle (e.g. overnight) without
  logging a miss.
- Hit/miss stats are saved to `stats.json` next to the app and persist across
  restarts and reboots.

## Building from source

Requires Python 3.10+ on Windows.

```bash
pip install pyinstaller
python make_icon.py   # regenerates icon.ico (needs Pillow: pip install pillow)
pyinstaller --onefile --windowed --icon=icon.ico --name AirSquat --add-data "icon.ico;." airsquat.py
```

The built exe will be in `dist/AirSquat.exe`.

Pushing a version tag (e.g. `v1.0.0`) triggers a GitHub Actions workflow that
builds the exe and attaches it to a new GitHub Release automatically.

## License

MIT — see [LICENSE](LICENSE).

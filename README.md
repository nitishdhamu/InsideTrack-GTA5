# InsideTrack-GTA5

Screen automation for GTA Online Diamond Casino Inside Track.

The bot uses only:

- screen capture
- OCR/image processing
- mouse input

It does not edit GTA files, inject into the game, read memory, use game APIs, or predict race results. It reads the visible odds, clicks the lowest-odds horse, places a max bet, waits for results, clicks Bet Again, and repeats. Automation may still violate GTA Online/Rockstar rules, so use it at your own risk.

## What It Does

1. Automatically detects and focuses the Grand Theft Auto V window (with a 2s grace period).
2. Detects the Inside Track screen.
3. Reads the six visible horse odds.
4. Selects the lowest odds horse.
5. Clicks the bet amount right arrow 27 times for the 10,000 max bet.
6. Places the bet.
7. Waits during the race.
8. Clicks Bet Again on the result screen.
9. Repeats until stopped.

Stop the bot anytime:

- **While in GTA**: Press `Ctrl + Q`
- **In Console**: Press `Ctrl + C` (or close the window)

## Requirements

- Windows 10 or Windows 11
- Tesseract OCR (installed via winget or installer)
- GTA running at 1920x1080 (Borderless Windowed recommended)

To install Tesseract OCR if you don't have it:

```bat
winget install -e --id UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements
```

## Quick Run

Simply double-click:

```bat
dist\InsideTrack.exe
```

1. The bot automatically finds GTA V, brings it to the front, and starts immediately.
2. If GTA isn't open yet, it continuously scans every 2 seconds until the game is detected and focused.
3. Open the Inside Track betting computer screen in the Diamond Casino.
4. The bot handles betting automatically.

## Test Without Clicking

Use dry-run mode if you want to confirm detection without sending mouse clicks:

```bat
dist\InsideTrack.exe --dry-run
```

## Recommended GTA Settings

```text
Display Type: Windowed Borderless
Resolution: 1920x1080
Pause Game On Focus Loss: Off
```

The bot is calibrated for 1920x1080. If your resolution is different, the click positions and OCR regions in `config.json` can be adjusted.

## Bet Amount

By default, the bot clicks the bet amount right arrow 27 times to reach the 10,000 max bet.

You can customize this in `config.json`:

```json
"bet_right_clicks": 27
```

Or override it temporarily from the command line:

```bat
dist\InsideTrack.exe --bet-right-clicks 5
```

The bet click timings can also be tuned in `config.json`:

```json
"bet_click_hold_seconds": 0.12,
"bet_post_move_delay_seconds": 0.05,
"bet_right_click_interval_seconds": 0.15
```

## Building from Source

If you edit `bot.py` and want to recompile `InsideTrack.exe`:

```bat
build.bat
```

This builds a fresh `dist\InsideTrack.exe` inside an isolated build environment without affecting your PC's Python packages.

## Files

- `dist\InsideTrack.exe` - standalone executable (zero Python install needed)
- `bot.py` - main bot source code
- `config.json` - screen coordinates, OCR regions, delays, bet settings
- `build.bat` - compiles bot.py into dist\InsideTrack.exe in an isolated build environment

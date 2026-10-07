from __future__ import annotations

import argparse
import copy
import ctypes
from ctypes import wintypes
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mss
import pydirectinput
import pytesseract
from PIL import Image, ImageFilter, ImageOps

try:
    import keyboard
except Exception:
    keyboard = None


def get_config_path() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "config.json").exists():
            return exe_dir / "config.json"
        if (exe_dir.parent / "config.json").exists():
            return exe_dir.parent / "config.json"
        return exe_dir / "config.json"
    return Path(__file__).resolve().parent / "config.json"


CONFIG_PATH = get_config_path()
STOP_HOTKEY = "ctrl+q"
_stop_requested = False


def print_banner() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    try:
        os.system("")
        ctypes.windll.kernel32.SetConsoleTitleW("InsideTrack-GTA5 | Diamond Casino Automation")
    except Exception:
        pass

    c_cyan = "\033[96m"
    c_yellow = "\033[93m"
    c_green = "\033[92m"
    c_white = "\033[97m"
    c_dim = "\033[90m"
    c_bold = "\033[1m"
    c_reset = "\033[0m"

    banner_lines = [
        "   ___           _     _    _____               _    ",
        "  |_ _|_ __  ___(_) __| |__|_   _| __ __ _  ___| | __",
        "   | || '_ \\/ __| |/ _` |/ _ \\| || '__/ _` |/ __| |/ /",
        "   | || | | \\__ \\ | (_| |  __/| || | | (_| | (__|   < ",
        "  |___|_| |_|___/_|\\__,_|\\___||_||_|  \\__,_|\\___|_|\\_\\",
    ]
    art = "\n".join(banner_lines)

    print(f"{c_cyan}{c_bold}{art}{c_reset}")
    print(f"{c_yellow}       Diamond Casino & Resort | Inside Track Automation{c_reset}")
    print(f"{c_dim}================================================================={c_reset}")
    print(f"  {c_bold}[+] Target Game{c_reset}       : {c_white}Grand Theft Auto V (1920x1080){c_reset}")
    print(f"  {c_bold}[+] Vision System{c_reset}     : {c_white}Pure Pillow + Tesseract OCR (0 MB Extra){c_reset}")
    print(f"  {c_bold}[+] Stop in GTA{c_reset}       : {c_green}{c_bold}Ctrl + Q{c_reset}")
    print(f"  {c_bold}[+] Stop in Console{c_reset}   : {c_yellow}{c_bold}Ctrl + C{c_reset}")
    print(f"{c_dim}================================================================={c_reset}\n")


def log_msg(icon: str, msg: str, color: str = "") -> None:
    now_str = time.strftime("%H:%M:%S")
    reset = "\033[0m" if color else ""
    print(f"  {color}[{icon}] [{now_str}] {msg}{reset}")


@dataclass(frozen=True)
class Region:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class OddsInfo:
    text: str
    rank_value: float
    probability: float


DEFAULT_CONFIG: dict[str, Any] = {
    "screen_width": 1920,
    "screen_height": 1080,
    "start_delay_seconds": 10,
    "poll_delay_seconds": 0.8,
    "race_poll_delay_seconds": 3.0,
    "post_click_delay_seconds": 1.2,
    "click_hold_seconds": 0.12,
    "post_move_delay_seconds": 0.05,
    "bet_click_hold_seconds": 0.12,
    "bet_post_move_delay_seconds": 0.05,
    "bet_right_click_interval_seconds": 0.15,
    "ocr_min_rows_required": 4,
    "bet_right_clicks": 27,
    "clicks": {
        "main_single_event_place_bet": [1445, 908],
        "betting_place_bet": [1280, 790],
        "result_bet_again": [960, 998],
        "horse_rows": [
            [335, 338],
            [335, 459],
            [335, 580],
            [335, 702],
            [335, 823],
            [335, 944],
        ],
        "bet_amount_left": [1052, 517],
        "bet_amount_right": [1518, 517],
    },
    "regions": {
        "state_top": [720, 20, 760, 180],
        "state_right": [960, 175, 670, 790],
        "state_betting_panel": [990, 380, 580, 340],
        "state_bottom": [650, 720, 820, 330],
        "odds_rows": [
            [175, 345, 150, 46],
            [175, 466, 150, 46],
            [175, 587, 150, 46],
            [175, 709, 150, 46],
            [175, 830, 150, 46],
            [175, 951, 150, 46],
        ],
    },
    "tesseract_cmd": "",
}


def load_config(path: Path) -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                user_config = json.load(f)
            config.update(user_config)
            log_msg("+", f"Loaded custom configuration: {path.name}")
        except Exception as exc:
            log_msg("!", f"Failed to parse {path.name} ({exc}), using defaults.", "\033[93m")
    else:
        log_msg("i", "No custom config.json found - using built-in defaults (1920x1080).")
    return config


def setup_tesseract(config: dict[str, Any]) -> None:
    configured = str(config.get("tesseract_cmd") or "").strip()
    candidates = [
        configured,
        shutil.which("tesseract") or "",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return

    raise RuntimeError(
        "Tesseract OCR was not found. Install it with winget or set "
        '"tesseract_cmd" in config.json.'
    )


def parse_region(raw: list[int]) -> Region:
    return Region(x=int(raw[0]), y=int(raw[1]), w=int(raw[2]), h=int(raw[3]))


def screenshot(sct: Any, width: int, height: int) -> Image.Image:
    monitor = {"top": 0, "left": 0, "width": width, "height": height}
    sct_img = sct.grab(monitor)
    return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")


def crop(img: Image.Image, region: Region) -> Image.Image:
    return img.crop((region.x, region.y, region.x + region.w, region.y + region.h))


def preprocess_for_ocr(img: Image.Image, scale: int = 3) -> Image.Image:
    gray = img.convert("L")
    w, h = gray.size
    gray = gray.resize((w * scale, h * scale), Image.Resampling.BICUBIC)
    gray = gray.filter(ImageFilter.GaussianBlur(radius=1))

    # Otsu thresholding
    hist = gray.histogram()
    total = (w * scale) * (h * scale)
    sum_total = sum(i * hist[i] for i in range(256))
    sum_b = 0
    w_b = 0
    max_var = 0.0
    threshold = 128
    for i in range(256):
        w_b += hist[i]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += i * hist[i]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        var_between = w_b * w_f * ((m_b - m_f) ** 2)
        if var_between > max_var:
            max_var = var_between
            threshold = i

    binary = gray.point(lambda p: 255 if p > threshold else 0)

    # Tesseract generally does better with dark text on a light background.
    avg_brightness = sum_total / total if total > 0 else 0
    if avg_brightness < 127:
        binary = ImageOps.invert(binary)
    return binary


def ocr_text(img: Image.Image, *, whitelist: str = "", psm: int = 6) -> str:
    processed = preprocess_for_ocr(img)
    config = f"--oem 3 --psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"
    try:
        return pytesseract.image_to_string(processed, config=config)
    except pytesseract.TesseractError:
        return ""


def normalized_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9/]", "", text.upper())


def detect_state(img: Image.Image, config: dict[str, Any]) -> str:
    regions = config["regions"]
    samples = [
        crop(img, parse_region(regions["state_top"])),
        crop(img, parse_region(regions["state_right"])),
        crop(img, parse_region(regions["state_betting_panel"])),
        crop(img, parse_region(regions["state_bottom"])),
    ]
    text = normalized_text(" ".join(ocr_text(sample, psm=6) for sample in samples))

    # Results screen: Post-race results with Bet Again button
    if "BETAGAIN" in text or ("PHOTOFINISH" in text and "RESULT" in text) or ("RESULT" in text and "WINNER" in text):
        return "results"

    # Betting screen: Bet amount setup with Place Bet button & Balance/Payout
    if ("CURRENTBALANCE" in text and "PAYOUT" in text) or ("PLACEBET" in text and ("PAYOUT" in text or "BETAMOUNT" in text)):
        return "betting"

    # Horse roster screen: Select Horse menu with list of runners
    if "SELECTHORSE" in text or ("SINGLEEVENT" in text and "CANCEL" in text):
        return "horse_selection"

    # Main menu: Inside Track terminal title with Single Event / Main Event buttons
    if ("INSIDETRACK" in text or "MAINEVENT" in text or "PLAYWITHYOURSELF" in text) and ("SINGLEEVENT" in text or "RULES" in text):
        return "main"

    return "race_or_unknown"


def parse_odds_info(raw_text: str) -> OddsInfo | None:
    text = normalized_text(raw_text)
    if not text:
        return None
    if "EVEN" in text or "FVENS" in text:
        return OddsInfo(text="1/1", rank_value=1.0, probability=0.5)

    text = (
        text.replace("I", "1")
        .replace("L", "1")
        .replace("O", "0")
        .replace("S", "5")
        .replace("B", "8")
    )
    match = re.search(r"(\d{1,3})/(\d{1,2})", text)
    if not match:
        match = re.search(r"(\d{1,3})", text)
    if not match:
        return None

    numerator = int(match.group(1))
    denominator = int(match.group(2)) if match.lastindex and match.lastindex >= 2 else 1
    if denominator <= 0:
        return None
    return OddsInfo(
        text=f"{numerator}/{denominator}",
        rank_value=numerator / denominator,
        probability=denominator / (numerator + denominator),
    )


def parse_odds(raw_text: str) -> float | None:
    odds = parse_odds_info(raw_text)
    return None if odds is None else odds.rank_value


def read_odds_details(img: Image.Image, config: dict[str, Any]) -> list[OddsInfo | None]:
    odds: list[OddsInfo | None] = []
    whitelist = "EVENS0123456789/"
    for raw_region in config["regions"]["odds_rows"]:
        region = parse_region(raw_region)
        text = ocr_text(crop(img, region), whitelist=whitelist, psm=7)
        odds.append(parse_odds_info(text))
    return odds


def read_odds(img: Image.Image, config: dict[str, Any]) -> list[float | None]:
    return [None if odds is None else odds.rank_value for odds in read_odds_details(img, config)]


def best_horse_index(odds: list[float | None], min_rows_required: int) -> int | None:
    readable = [(index, value) for index, value in enumerate(odds) if value is not None]
    if len(readable) < min_rows_required:
        return None
    readable.sort(key=lambda item: (item[1], item[0]))
    return readable[0][0]


def click_point(
    point: list[int],
    config: dict[str, Any],
    dry_run: bool,
    label: str,
    *,
    hold_seconds: float | None = None,
    post_move_delay: float | None = None,
) -> None:
    x, y = int(point[0]), int(point[1])
    if hold_seconds is None:
        hold_seconds = float(config.get("click_hold_seconds", 0.12))
    if post_move_delay is None:
        post_move_delay = float(config.get("post_move_delay_seconds", 0.05))

    print(f"{label}: click at ({x}, {y})")
    if dry_run:
        return

    pydirectinput.moveTo(x, y)
    time.sleep(post_move_delay)
    pydirectinput.mouseDown(button="left")
    time.sleep(hold_seconds)
    pydirectinput.mouseUp(button="left")


def find_gta_window() -> int:
    """Finds the HWND for Grand Theft Auto V via direct class/title or window enumeration."""
    try:
        user32 = ctypes.windll.user32
        for cls, title in [
            ("grcWindow", "Grand Theft Auto V"),
            (None, "Grand Theft Auto V"),
            ("grcWindow", None),
        ]:
            hwnd = user32.FindWindowW(cls, title)
            if hwnd and user32.IsWindow(hwnd):
                return hwnd

        matched_hwnd = 0
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, ctypes.c_void_p)

        def enum_cb(h: int, _: Any) -> bool:
            nonlocal matched_hwnd
            if user32.IsWindowVisible(h):
                length = user32.GetWindowTextLengthW(h)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(h, buf, length + 1)
                    val = buf.value.lower()
                    if "grand theft auto" in val or val == "gta5":
                        matched_hwnd = h
                        return False
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return matched_hwnd
    except Exception:
        return 0


def focus_gta_window() -> bool:
    """Attempts to find and smoothly bring the GTA V window to the foreground."""
    hwnd = find_gta_window()
    if hwnd:
        try:
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            pass
    return False


def is_gta_active() -> bool:
    """Returns True if Grand Theft Auto V is currently the active foreground window."""
    try:
        gta_hwnd = find_gta_window()
        if not gta_hwnd:
            return False
        user32 = ctypes.windll.user32
        fg_hwnd = user32.GetForegroundWindow()
        if not fg_hwnd:
            return False
        if fg_hwnd == gta_hwnd:
            return True
        pid_fg = wintypes.DWORD()
        pid_gta = wintypes.DWORD()
        user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(pid_fg))
        user32.GetWindowThreadProcessId(gta_hwnd, ctypes.byref(pid_gta))
        return bool(pid_fg.value == pid_gta.value and pid_gta.value != 0)
    except Exception:
        return False


def wait_for_gta(start_delay: float | None = None) -> bool:
    """Continuously checks for GTA V until detected and focused."""
    log_msg("*", "Detecting Grand Theft Auto V window...")
    if focus_gta_window():
        log_msg("+", "Found Grand Theft Auto V! Switched to game window.", "\033[92m")
        if start_delay is not None:
            log_msg("*", f"Custom start delay: waiting {start_delay:g} seconds...")
            if interruptible_sleep(start_delay):
                log_msg("!", "Stopped before start.", "\033[93m")
                return False
        else:
            time.sleep(0.5)
        return True

    log_msg("!", "Grand Theft Auto V window was not detected.", "\033[93m")
    log_msg("*", "Scanning for GTA V every 2 seconds... (Press Ctrl+C to cancel)")

    while not should_stop():
        if focus_gta_window():
            log_msg("+", "Grand Theft Auto V detected! Switched to game window.", "\033[92m")
            time.sleep(0.5)
            return True
        if interruptible_sleep(2.0):
            return False

    return False


def request_stop() -> None:
    global _stop_requested
    _stop_requested = True


def setup_stop_hotkeys() -> None:
    if keyboard is None:
        return
    try:
        keyboard.add_hotkey(STOP_HOTKEY, request_stop)
    except Exception:
        pass


def should_stop() -> bool:
    global _stop_requested
    if _stop_requested:
        return True
    if keyboard is not None:
        try:
            if keyboard.is_pressed(STOP_HOTKEY):
                _stop_requested = True
                return True
        except Exception:
            pass
    return False


def interruptible_sleep(seconds: float) -> bool:
    """Sleeps in 50ms intervals and exits immediately if stop was requested."""
    end_time = time.time() + max(0.0, seconds)
    while time.time() < end_time:
        if should_stop():
            return True
        remaining = end_time - time.time()
        time.sleep(min(0.05, max(0.005, remaining)))
    return False


def handle_main(config: dict[str, Any], dry_run: bool) -> None:
    click_point(config["clicks"]["main_single_event_place_bet"], config, dry_run, "main")


def handle_horse_selection(
    img: Image.Image,
    config: dict[str, Any],
    dry_run: bool,
) -> int | None:
    odds = read_odds(img, config)
    printable = ["?" if value is None else f"{value:g}/1" for value in odds]
    log_msg("*", f"Odds: {printable}")

    index = best_horse_index(odds, int(config.get("ocr_min_rows_required", 4)))
    if index is None:
        log_msg("!", "Odds OCR incomplete; waiting for a clearer frame...", "\033[93m")
        return None

    selected_horse_no = index + 1
    lowest_odds = odds[index]
    row_point = config["clicks"]["horse_rows"][index]
    log_msg("+", f"Selected Horse #{selected_horse_no} (Lowest Odds: {lowest_odds:g}/1)", "\033[92m")
    click_point(row_point, config, dry_run, f"horse {selected_horse_no}")

    return selected_horse_no


def handle_betting(
    config: dict[str, Any],
    dry_run: bool,
    override_right_clicks: int | None,
) -> bool:
    right_clicks = int(config.get("bet_right_clicks", 0))
    if override_right_clicks is not None:
        right_clicks = override_right_clicks

    if right_clicks > 0:
        bet_hold_seconds = float(config.get("bet_click_hold_seconds", 0.12))
        bet_post_move_delay = float(config.get("bet_post_move_delay_seconds", 0.05))
        bet_click_interval = float(config.get("bet_right_click_interval_seconds", 0.15))
        log_msg("*", f"Setting max bet ({right_clicks} clicks)...")
        for click_number in range(right_clicks):
            if should_stop():
                return False
            click_point(
                config["clicks"]["bet_amount_right"],
                config,
                dry_run,
                f"bet amount right {click_number + 1}/{right_clicks}",
                hold_seconds=bet_hold_seconds,
                post_move_delay=bet_post_move_delay,
            )
            if interruptible_sleep(bet_click_interval):
                return False

    if should_stop():
        return False
    log_msg(">", "Placing bet...")
    click_point(config["clicks"]["betting_place_bet"], config, dry_run, "betting")
    return True


def handle_results(config: dict[str, Any], dry_run: bool) -> None:
    log_msg(">", "Clicking Bet Again...")
    click_point(config["clicks"]["result_bet_again"], config, dry_run, "results")


def run_bot(args: argparse.Namespace) -> int:
    print_banner()

    config = load_config(Path(args.config))
    if args.click_hold_seconds is not None:
        config["click_hold_seconds"] = args.click_hold_seconds

    setup_tesseract(config)
    setup_stop_hotkeys()

    pydirectinput.PAUSE = 0.05

    width = int(config["screen_width"])
    height = int(config["screen_height"])
    start_delay = float(args.start_delay if args.start_delay is not None else config["start_delay_seconds"])
    poll_delay = float(config["poll_delay_seconds"])
    race_poll_delay = float(config["race_poll_delay_seconds"])
    post_click_delay = float(config["post_click_delay_seconds"])

    if args.dry_run:
        log_msg("!", "Dry run enabled: no clicks will be sent.", "\033[93m")

    if not wait_for_gta(args.start_delay):
        log_msg("!", "Bot stopped.", "\033[93m")
        return 0

    log_msg("+", "Bot active. Monitoring Inside Track screen...", "\033[92m")
    last_state = ""
    loop_count = 0
    paused_notice_shown = False
    with mss.MSS() as sct:
        while not should_stop():
            if not args.dry_run and not is_gta_active():
                if not paused_notice_shown:
                    log_msg("*", "GTA V window is not focused. Pausing automation (checking every 2s)...", "\033[93m")
                    paused_notice_shown = True
                if interruptible_sleep(2.0):
                    break
                continue

            if paused_notice_shown:
                log_msg("+", "GTA V window focused. Resuming automation...", "\033[92m")
                paused_notice_shown = False
                time.sleep(0.3)
            img = screenshot(sct, width, height)
            state = detect_state(img, config)
            if state != last_state:
                if state == "race_or_unknown":
                    log_msg("*", "State: Waiting for Inside Track screen (or race in progress)...", "\033[96m")
                else:
                    log_msg("*", f"State: {state.replace('_', ' ').title()}", "\033[96m")
                last_state = state

            if state == "main":
                handle_main(config, args.dry_run)
                if interruptible_sleep(post_click_delay):
                    break
            elif state == "horse_selection":
                handle_horse_selection(img, config, args.dry_run)
                if interruptible_sleep(post_click_delay):
                    break
            elif state == "betting":
                if not handle_betting(config, args.dry_run, args.bet_right_clicks):
                    break
                if interruptible_sleep(post_click_delay):
                    break
            elif state == "results":
                handle_results(config, args.dry_run)
                loop_count += 1
                log_msg("+", f"Completed race loop #{loop_count}", "\033[92m")
                if interruptible_sleep(post_click_delay):
                    break
            else:
                if interruptible_sleep(race_poll_delay):
                    break

            if args.once:
                log_msg("i", "--once enabled; stopping after one action cycle.")
                break

            if interruptible_sleep(poll_delay):
                break

    log_msg("!", "Bot stopped.", "\033[93m")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="InsideTrack-GTA5: GTA Online Diamond Casino Inside Track automation.")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Path to config.json.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without clicking.")
    parser.add_argument("--once", action="store_true", help="Stop after one detected action cycle.")
    parser.add_argument("--start-delay", type=float, default=None, help="Override startup delay seconds.")
    parser.add_argument(
        "--bet-right-clicks",
        type=int,
        default=None,
        help="Override how many times to click the bet amount right arrow.",
    )
    parser.add_argument(
        "--click-hold-seconds",
        type=float,
        default=None,
        help="Override how long to hold the left mouse button.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run_bot(args)
    except KeyboardInterrupt:
        print()
        log_msg("!", "Console interrupt (Ctrl+C). Bot stopped.", "\033[93m")
        return 0
    except Exception as exc:
        log_msg("!", f"Error: {exc}", "\033[91m")
        if getattr(sys, "frozen", False):
            try:
                input("\nPress Enter to exit...")
            except Exception:
                pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

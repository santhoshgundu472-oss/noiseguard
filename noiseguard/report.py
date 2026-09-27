"""
NoiseGuard — Report
Formats and prints the final comparison table to stdout.
Uses only stdlib — no rich, no curses, no external dependency.
colorama is used for colour if installed, silently falls back to plain text.
"""
from typing import List

from noiseguard.compare import CircuitResult

try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init(autoreset=True)
    _GREEN  = Fore.GREEN
    _RED    = Fore.RED
    _YELLOW = Fore.YELLOW
    _RESET  = Style.RESET_ALL
except ImportError:
    _GREEN = _RED = _YELLOW = _RESET = ""


def _delta_str(delta: float | None) -> str:
    if delta is None:
        return "   —   "
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.4f}"


def _fid_str(val: float | None) -> str:
    return f"{val:.4f}" if val is not None else "  —    "


def print_report(results: List[CircuitResult], mem_on: bool, pec_on: bool) -> None:
    mitigation_label = f"MEM={'ON' if mem_on else 'OFF'}  PEC={'ON' if pec_on else 'OFF'}"

    header = (
        f"\nNoiseGuard Report  [{mitigation_label}]\n"
        + "─" * 92
    )
    print(header)

    col = "{:<16} {:>10} {:>10} {:>10} {:>9} {:>9} {:>9}  {}"
    print(col.format(
        "Circuit", "Raw Fid", "MEM Fid", "PEC Fid",
        "Raw Δ", "MEM Δ", "PEC Δ", "Status"
    ))
    print("─" * 92)

    for r in results:
        status = (
            f"{_GREEN}✅ PASS{_RESET}" if r.passed
            else f"{_RED}🚨 FAIL{_RESET}"
        )
        print(col.format(
            r.name,
            _fid_str(r.current_raw),
            _fid_str(r.current_mem),
            _fid_str(r.current_pec),
            _delta_str(r.delta_raw),
            _delta_str(r.delta_mem),
            _delta_str(r.delta_pec),
            status,
        ))
        if not r.passed:
            print(f"  {_YELLOW}↳ {r.fail_reason}{_RESET}")

    print("─" * 92)

    failures = [r for r in results if not r.passed]
    if failures:
        print(
            f"{_RED}RESULT: {len(failures)} circuit(s) FAILED — "
            f"noise model regression detected.{_RESET}"
        )
    else:
        print(f"{_GREEN}RESULT: All circuits passed.{_RESET}")
    print()

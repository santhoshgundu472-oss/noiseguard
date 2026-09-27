"""
NoiseGuard — Compare
Loads baseline.json and diffs current fidelity scores against it.
Returns a structured result for each circuit: pass/fail + deltas.
"""
import json
from dataclasses import dataclass
from typing import Dict, Optional

from noiseguard import config


@dataclass
class CircuitResult:
    name: str
    # Baseline values
    baseline_raw: float
    baseline_mem: float
    baseline_pec: Optional[float]
    # Current values
    current_raw: float
    current_mem: float
    current_pec: Optional[float]
    # Derived
    delta_raw: float
    delta_mem: float
    delta_pec: Optional[float]
    passed: bool
    fail_reason: str = ""


def load_baseline() -> Dict:
    try:
        with open(config.BASELINE_PATH) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"NoiseGuard: baseline.json is not valid JSON — {exc}\n"
            f"Run: python -m noiseguard.guard --update-baseline"
        ) from exc
    if not data:
        # File exists but is empty ({}) — no baseline seeded yet.
        raise SystemExit(
            "NoiseGuard: baseline.json is empty — no baseline has been seeded yet.\n"
            "Run: python -m noiseguard.guard --update-baseline"
        )
    return data


def save_baseline(scores: Dict[str, Dict[str, float]]) -> None:
    with open(config.BASELINE_PATH, "w") as f:
        json.dump(scores, f, indent=2)
    print(f"Baseline saved to {config.BASELINE_PATH}")


def compare(
    circuit_name: str,
    fidelity_scores: Dict[str, float],
    baseline: Dict,
) -> CircuitResult:
    """
    Compare current fidelity scores against baseline for one circuit.
    Uses per-circuit threshold from config, falling back to global.
    """
    threshold = config.PER_CIRCUIT_THRESHOLD.get(
        circuit_name, config.FIDELITY_DROP_THRESHOLD
    )

    b = baseline.get(circuit_name, {})
    b_raw = b.get("raw_fidelity", 1.0)
    b_mem = b.get("mem_fidelity", 1.0)
    b_pec = b.get("pec_fidelity", None)

    c_raw = fidelity_scores["raw"]
    c_mem = fidelity_scores["mem"]
    c_pec = fidelity_scores.get("pec", None)

    d_raw = c_raw - b_raw
    d_mem = c_mem - b_mem
    d_pec = (c_pec - b_pec) if (c_pec is not None and b_pec is not None) else None

    # Fail if the MEM-corrected fidelity drops more than threshold
    # (MEM is the authoritative signal; raw can fluctuate with shot noise)
    passed = True
    fail_reason = ""
    if d_mem < -threshold:
        passed = False
        fail_reason = f"MEM fidelity dropped {d_mem:+.4f} (threshold -{threshold})"
    elif d_raw < -threshold and d_mem < 0:
        # Both raw and MEM dropped — reinforce failure
        passed = False
        fail_reason = f"Raw fidelity dropped {d_raw:+.4f} and MEM confirms regression"

    return CircuitResult(
        name=circuit_name,
        baseline_raw=b_raw,
        baseline_mem=b_mem,
        baseline_pec=b_pec,
        current_raw=c_raw,
        current_mem=c_mem,
        current_pec=c_pec,
        delta_raw=d_raw,
        delta_mem=d_mem,
        delta_pec=d_pec,
        passed=passed,
        fail_reason=fail_reason,
    )


def compare_all(
    all_fidelity: Dict[str, Dict[str, float]],
) -> list[CircuitResult]:
    baseline = load_baseline()
    return [
        compare(name, scores, baseline)
        for name, scores in all_fidelity.items()
    ]

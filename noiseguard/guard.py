"""
NoiseGuard — CLI Entry Point

Usage:
  python -m noiseguard.guard                    # run checks, exit 0 (pass) or 1 (fail)
  python -m noiseguard.guard --run              # same as above (explicit)
  python -m noiseguard.guard --update-baseline  # reseed baseline.json
  python -m noiseguard.guard --watsonx          # predict via watsonx.ai (or stub)
  python -m noiseguard.guard --help
"""
import argparse
import sys
import warnings

# Suppress Qiskit deprecation warnings — keeps demo output clean
warnings.filterwarnings("ignore", category=DeprecationWarning)

from noiseguard import config
from noiseguard import noise_model as nm_module
from noiseguard import runner, fidelity, compare, report
from noiseguard.mitigate import mitigate_run
from noiseguard.circuits import BENCHMARK_CIRCUITS
from noiseguard.watsonx import predict_fidelity, explain_regression


def _run_pipeline() -> list:
    """
    Full pipeline: run → mitigate → fidelity → compare.
    Returns list[CircuitResult].
    """
    print("NoiseGuard: loading noise model...")
    noise_model = nm_module.build()

    print(f"NoiseGuard: running {len(BENCHMARK_CIRCUITS)} benchmark circuit(s)...")
    run_results = runner.run_all(noise_model)

    all_fidelity = {}
    for rr in run_results:
        print(f"  · {rr.name}: computing fidelity (MEM={'on'}, PEC={'on' if config.USE_PEC and rr.name in config.PEC_CIRCUITS else 'off'})...")
        mitigation_output = mitigate_run(rr, noise_model)
        all_fidelity[rr.name] = fidelity.compute_all(rr, mitigation_output)

    return compare.compare_all(all_fidelity)


def cmd_run() -> int:
    """Run checks and return exit code."""
    results = _run_pipeline()
    report.print_report(results, mem_on=config.MEM_ENABLED, pec_on=config.USE_PEC)
    failures = [r for r in results if not r.passed]
    return 1 if failures else 0


def cmd_update_baseline() -> int:
    """Reseed baseline.json from a fresh run."""
    print("NoiseGuard: reseeding baseline...")
    noise_model = nm_module.build()
    run_results = runner.run_all(noise_model)

    new_baseline = {}
    for rr in run_results:
        mitigation_output = mitigate_run(rr, noise_model)
        scores = fidelity.compute_all(rr, mitigation_output)
        new_baseline[rr.name] = {
            "raw_fidelity": scores["raw"],
            "mem_fidelity": scores["mem"],
            "pec_fidelity": scores["pec"],
        }

    compare.save_baseline(new_baseline)

    # Pretty-print what was stored
    print("\nNew baseline:")
    for name, vals in new_baseline.items():
        pec_str = f"{vals['pec_fidelity']:.4f}" if vals["pec_fidelity"] is not None else "—"
        print(f"  {name:<16}  raw={vals['raw_fidelity']:.4f}  mem={vals['mem_fidelity']:.4f}  pec={pec_str}")
    return 0


def cmd_watsonx() -> int:
    """
    watsonx-assisted mode: predict fidelity from noise parameters (no simulation),
    then explain any regressions in plain English.
    Falls back to a clearly-labelled heuristic stub when credentials are absent.
    """
    from noiseguard.watsonx.predictor import _watsonx_available
    mode = "watsonx.ai" if _watsonx_available() else "heuristic stub"
    print(f"NoiseGuard [watsonx mode — {mode}]")
    print(f"Noise parameters: SQ={config.SINGLE_QUBIT_ERROR_RATE}  "
          f"TQ={config.TWO_QUBIT_ERROR_RATE}  RO={config.READOUT_ERROR_RATE}\n")

    noise_params = {
        "single_qubit_error_rate": config.SINGLE_QUBIT_ERROR_RATE,
        "two_qubit_error_rate":    config.TWO_QUBIT_ERROR_RATE,
        "readout_error_rate":      config.READOUT_ERROR_RATE,
    }

    baseline = compare.load_baseline()
    failures = 0

    for circuit_name in [b.NAME for b in BENCHMARK_CIRCUITS]:
        params = {**noise_params, "circuit": circuit_name}
        predicted = predict_fidelity(params)

        b = baseline.get(circuit_name, {})
        baseline_mem = b.get("mem_fidelity", 1.0)
        threshold = config.PER_CIRCUIT_THRESHOLD.get(
            circuit_name, config.FIDELITY_DROP_THRESHOLD
        )
        delta = predicted - baseline_mem
        passed = delta >= -threshold

        result = {
            "circuit":           circuit_name,
            "baseline_fidelity": baseline_mem,
            "current_fidelity":  predicted,
            "threshold":         threshold,
            "passed":            passed,
        }
        explanation = explain_regression(result)
        status = "✅ PASS" if passed else "🚨 FAIL"
        print(f"  {circuit_name:<16}  predicted={predicted:.4f}  "
              f"baseline={baseline_mem:.4f}  Δ={delta:+.4f}  {status}")
        print(f"  {explanation}\n")

        if not passed:
            failures += 1

    if failures:
        print(f"RESULT: {failures} circuit(s) flagged by watsonx prediction.")
        return 1
    print("RESULT: All circuits passed watsonx prediction check.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="noiseguard",
        description="NoiseGuard — quantum noise model regression detector",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run benchmark circuits and compare against baseline (default action)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Reseed baseline.json from a fresh run of all benchmark circuits",
    )
    parser.add_argument(
        "--watsonx",
        action="store_true",
        help="Predict fidelity via watsonx.ai (falls back to heuristic stub if unconfigured)",
    )
    args = parser.parse_args()

    if args.update_baseline:
        sys.exit(cmd_update_baseline())
    elif args.watsonx:
        sys.exit(cmd_watsonx())
    else:
        # Default: run checks (whether or not --run is passed explicitly)
        sys.exit(cmd_run())


if __name__ == "__main__":
    main()

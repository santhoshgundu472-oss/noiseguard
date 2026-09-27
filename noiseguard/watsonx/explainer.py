"""
watsonx-ready natural-language explainer for NoiseGuard regressions.

Once wired up, this would call a watsonx.ai foundation model to turn a
compare.py result into a plain-English explanation for report.py. Until
then it returns a templated explanation so guard.py --watsonx has a
stable string either way.
"""

from .predictor import _watsonx_available


def explain_regression(result: dict) -> str:
    """
    Given a compare.py-style result dict:
        {
          "circuit":           str,
          "baseline_fidelity": float,
          "current_fidelity":  float,
          "threshold":         float,
          "passed":            bool,
        }
    Returns a one-paragraph plain-English explanation.
    Callers never need to check whether watsonx is available.
    """
    if _watsonx_available():
        return _explain_with_watsonx(result)
    return _explain_stub(result)


def _explain_with_watsonx(result: dict) -> str:
    # TODO: replace with a real ibm_watsonx_ai foundation-model call
    # (prompt built from `result`) once a deployment exists.
    raise NotImplementedError(
        "watsonx credentials found, but no foundation-model deployment is "
        "wired up yet."
    )


def _explain_stub(result: dict) -> str:
    circuit   = result.get("circuit", "unknown circuit")
    baseline  = result.get("baseline_fidelity")
    current   = result.get("current_fidelity")
    threshold = result.get("threshold")
    passed    = result.get("passed")

    if passed:
        return (
            f"[watsonx stub] {circuit}: fidelity held at {current:.4f} "
            f"(baseline {baseline:.4f}, threshold {threshold}) — no regression detected."
        )

    delta = (current - baseline) if (baseline is not None and current is not None) else None
    return (
        f"[watsonx stub] {circuit}: fidelity dropped to {current:.4f} from a "
        f"baseline of {baseline:.4f}"
        + (f" (delta {delta:+.4f})" if delta is not None else "")
        + f", past the {threshold} threshold — likely a real noise-model "
          f"regression, not shot noise."
    )

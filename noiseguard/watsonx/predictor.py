"""
watsonx-ready fidelity predictor for NoiseGuard.

When IBM watsonx.ai credentials are present *and* a trained model/deployment
exists, this predicts the MEM-corrected fidelity a circuit would see under a
given set of noise parameters, without having to run the noisy simulation.

Right now there isn't a trained model (one dry run isn't training data), so
this falls back to a transparent, clearly-labelled heuristic stub. The point
is that guard.py --watsonx has a stable function to call either way; nothing
downstream has to change when a real deployment goes live.
"""

import os


def _watsonx_available() -> bool:
    """True only if credentials are present AND the SDK is installed."""
    # Read at call time so env vars set after import are picked up correctly
    if not (os.environ.get("WATSONX_API_KEY") and os.environ.get("WATSONX_PROJECT_ID")):
        return False
    try:
        import ibm_watsonx_ai  # noqa: F401
        return True
    except ImportError:
        return False


def predict_fidelity(noise_params: dict) -> float:
    """
    Predict MEM-corrected fidelity for a circuit given its noise parameters,
    e.g. {"two_qubit_error_rate": 0.15, "circuit": "ghz_3qubit"}.

    Returns a float in [0, 1]. Callers never need to branch on whether
    watsonx is configured — this handles that internally.
    """
    if _watsonx_available():
        return _predict_with_watsonx(noise_params)
    return _predict_stub(noise_params)


def _predict_with_watsonx(noise_params: dict) -> float:
    # TODO: point this at a real ibm_watsonx_ai deployment once one exists.
    # Wiring stays isolated here so nothing else in the pipeline changes
    # when this goes live.
    from ibm_watsonx_ai import Credentials, APIClient  # type: ignore

    credentials = Credentials(
        api_key=os.environ.get("WATSONX_API_KEY"),
        url="https://us-south.ml.cloud.ibm.com",
    )
    client = APIClient(credentials)
    client.set.default_project(os.environ.get("WATSONX_PROJECT_ID"))

    raise NotImplementedError(
        "watsonx credentials found, but no trained model/deployment ID is "
        "wired up yet. Point this at a real deployment before relying on it."
    )


def _predict_stub(noise_params: dict) -> float:
    """
    Deterministic, explainable placeholder that penalizes fidelity roughly
    linearly with two_qubit_error_rate, matching the shape of NoiseGuard's
    depolarizing model. This is NOT a trained prediction — it is clearly
    logged as a stub so nothing pretends to be more than it is.
    """
    base_fidelity = 0.999
    error_rate = noise_params.get("two_qubit_error_rate", 0.0)
    predicted = base_fidelity - (error_rate * 0.9)
    print(
        f"[watsonx stub] no credentials/model configured — returning a "
        f"heuristic estimate for {noise_params}, not a trained prediction"
    )
    return max(0.0, min(1.0, predicted))

"""
NoiseGuard — Fidelity
Computes classical fidelity (Bhattacharyya coefficient) between the ideal
probability distribution derived from a Statevector and a measured/mitigated
probability distribution from counts.

F = Σ sqrt(p_ideal_i · p_measured_i)

This is the correct metric when you have shot-based counts rather than the
full quantum state. It ranges from 0 (no overlap) to 1 (perfect match) and
correctly handles entangled states like Bell and GHZ where a diagonal density
matrix comparison would always read ~0.5 regardless of noise.
"""
from typing import Dict

import numpy as np
from qiskit.quantum_info import Statevector

from noiseguard.runner import RunResult


def _ideal_probs(ideal_sv: Statevector, num_qubits: int) -> np.ndarray:
    """Extract probability distribution from a Statevector."""
    probs = np.abs(ideal_sv.data) ** 2
    # Ensure length matches 2^n (Statevector.dim is already 2^n for n qubits)
    assert len(probs) == 2 ** num_qubits, (
        f"Statevector length {len(probs)} does not match 2^{num_qubits}"
    )
    return probs


def _counts_to_probs(
    quasi_counts: Dict[str, float],
    num_qubits: int,
) -> np.ndarray:
    """Convert a bitstring → probability dict to a dense probability vector."""
    n_states = 2 ** num_qubits
    probs = np.zeros(n_states)
    for bitstr, prob in quasi_counts.items():
        probs[int(bitstr, 2)] = prob
    return probs


def compute(
    ideal_sv: Statevector,
    quasi_counts: Dict[str, float],
    num_qubits: int,
) -> float:
    """
    Classical fidelity (Bhattacharyya coefficient) between the ideal
    probability distribution and the measured/mitigated distribution.
    Returns F ∈ [0, 1].
    """
    p_ideal = _ideal_probs(ideal_sv, num_qubits)
    p_meas = _counts_to_probs(quasi_counts, num_qubits)
    return float(np.sum(np.sqrt(p_ideal * p_meas)))


def compute_all(
    run_result: RunResult,
    mitigation_output: Dict[str, Dict],
) -> Dict[str, float]:
    """
    Given a RunResult and mitigate_run() output, return:
        {
          "raw":  float,
          "mem":  float,
          "pec":  float | None,
        }
    """
    n = run_result.num_qubits
    total = sum(run_result.noisy_counts.values())
    raw_probs = {k: v / total for k, v in run_result.noisy_counts.items()}

    raw_fidelity = compute(run_result.ideal_sv, raw_probs, n)
    mem_fidelity = compute(run_result.ideal_sv, mitigation_output["mem"], n)

    pec_fidelity = None
    if mitigation_output.get("pec") is not None:
        pec_fidelity = compute(run_result.ideal_sv, mitigation_output["pec"], n)

    return {
        "raw": raw_fidelity,
        "mem": mem_fidelity,
        "pec": pec_fidelity,
    }

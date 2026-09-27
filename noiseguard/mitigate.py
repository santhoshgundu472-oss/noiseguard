"""
NoiseGuard — Mitigation
Strategy-pattern implementation so new methods (ZNE, etc.) are drop-in additions.

Layer 1 (always):  MEM — corrects readout / SPAM errors via calibration matrix
Layer 2 (opt-in):  PEC — corrects gate errors via quasi-probability sampling

Usage:
    from noiseguard.mitigate import get_strategy
    strategy = get_strategy("mem")            # or "pec", "none"
    mitigated_counts = strategy.mitigate(run_result, noise_model)
"""
from __future__ import annotations

import abc
from typing import Dict

import numpy as np
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

from noiseguard import config
from noiseguard.runner import RunResult
from noiseguard.circuits import BENCHMARK_CIRCUITS


# =============================================================================
# Base strategy interface
# =============================================================================

class MitigationStrategy(abc.ABC):
    @abc.abstractmethod
    def mitigate(
        self,
        run_result: RunResult,
        noise_model: NoiseModel,
    ) -> Dict[str, float]:
        """
        Returns quasi-counts (float values) after mitigation.
        MEM output is always positive; PEC may produce negative entries.
        """


# =============================================================================
# Layer 1 — Measurement Error Mitigation (MEM)
# =============================================================================

class MEMStrategy(MitigationStrategy):
    """
    Corrects readout errors by inverting the calibration (assignment) matrix.

    Calibration: run each computational basis state |i⟩, record which states
    the device actually reports. This builds an n×n stochastic matrix A where
    A[j][i] = P(measure j | prepared i).

    Correction: solve  A · p_mitigated = p_noisy  for p_mitigated.
    """

    def _build_calibration_matrix(
        self,
        num_qubits: int,
        noise_model: NoiseModel,
    ) -> np.ndarray:
        from qiskit import QuantumCircuit, transpile

        sim = AerSimulator(noise_model=noise_model)
        n_states = 2 ** num_qubits
        cal_matrix = np.zeros((n_states, n_states))

        for i in range(n_states):
            qc = QuantumCircuit(num_qubits, num_qubits)
            # Prepare |i⟩
            for bit, val in enumerate(format(i, f"0{num_qubits}b")[::-1]):
                if val == "1":
                    qc.x(bit)
            qc.measure(range(num_qubits), range(num_qubits))
            transpiled = transpile(qc, sim)
            counts = sim.run(transpiled, shots=config.SHOTS).result().get_counts()
            for j_str, cnt in counts.items():
                j = int(j_str, 2)
                cal_matrix[j][i] = cnt / config.SHOTS

        return cal_matrix

    def mitigate(
        self,
        run_result: RunResult,
        noise_model: NoiseModel,
    ) -> Dict[str, float]:
        n = run_result.num_qubits
        n_states = 2 ** n

        cal_matrix = self._build_calibration_matrix(n, noise_model)

        # Build raw probability vector
        p_noisy = np.zeros(n_states)
        total = sum(run_result.noisy_counts.values())
        for bitstr, cnt in run_result.noisy_counts.items():
            idx = int(bitstr, 2)
            p_noisy[idx] = cnt / total

        # Invert calibration matrix (least-squares for numerical stability)
        p_mitigated, _, _, _ = np.linalg.lstsq(cal_matrix, p_noisy, rcond=None)

        # Convert back to quasi-counts dict (clip negatives to 0 for MEM)
        p_mitigated = np.clip(p_mitigated, 0, None)
        total = p_mitigated.sum()
        if total == 0:
            # Degenerate case: fall back to uniform distribution
            p_mitigated = np.ones(n_states) / n_states
        else:
            p_mitigated /= total

        return {
            format(i, f"0{n}b"): float(p_mitigated[i])
            for i in range(n_states)
            if p_mitigated[i] > 0
        }


# =============================================================================
# Layer 2 — Probabilistic Error Cancellation (PEC)
# =============================================================================

class PECStrategy(MitigationStrategy):
    """
    Corrects gate errors on top of MEM via quasi-probability decomposition.

    For each noisy gate G_noisy, express it as a linear combination of
    implementable operations: G_ideal = Σ c_i · O_i  where c_i can be negative.
    Sample operations proportionally to |c_i|, run the circuit, weight the
    outcome by sign(c_i). Average over many samples → unbiased estimate.

    Note: this implementation uses noise amplification + Richardson extrapolation
    (ZNE-style) as a practical PEC approximation suitable for a simulator.
    Full quasi-probability decomposition requires gate-set tomography which is
    out of scope for a 48-hour build.
    """

    def _run_at_scale(
        self,
        run_result: RunResult,
        noise_model: NoiseModel,
        scale: float,
    ) -> np.ndarray:
        """Run the circuit with noise scaled by `scale`, return prob vector."""
        from qiskit import transpile
        from qiskit_aer.noise import NoiseModel as NM, depolarizing_error, ReadoutError

        # Build a scaled noise model
        scaled = NM()
        sq = depolarizing_error(
            min(config.SINGLE_QUBIT_ERROR_RATE * scale, 0.999), 1
        )
        tq = depolarizing_error(
            min(config.TWO_QUBIT_ERROR_RATE * scale, 0.999), 2
        )
        p = min(config.READOUT_ERROR_RATE * scale, 0.499)
        ro = ReadoutError([[1 - p, p], [p, 1 - p]])
        scaled.add_all_qubit_quantum_error(sq, ["h", "x", "rz", "sx", "u"])
        scaled.add_all_qubit_quantum_error(tq, ["cx"])
        scaled.add_all_qubit_readout_error(ro)

        sim = AerSimulator(noise_model=scaled)
        circuit_module = next(
            m for m in BENCHMARK_CIRCUITS if m.NAME == run_result.name
        )
        qc = transpile(circuit_module.build(), sim)
        shots = config.SHOTS * config.PEC_SHOTS_MULTIPLIER
        counts = sim.run(qc, shots=shots).result().get_counts()

        n = run_result.num_qubits
        n_states = 2 ** n
        total = sum(counts.values())
        p_vec = np.zeros(n_states)
        for bitstr, cnt in counts.items():
            p_vec[int(bitstr, 2)] = cnt / total
        return p_vec

    def mitigate(
        self,
        run_result: RunResult,
        noise_model: NoiseModel,
    ) -> Dict[str, float]:
        # Richardson extrapolation with scale factors [1, 2, 3]
        scales = config.PEC_NOISE_AMPLIFICATION_FACTORS
        probs = [self._run_at_scale(run_result, noise_model, s) for s in scales]

        # Linear extrapolation to zero noise
        # For two-point: p0 = 2*p(1) - p(2)
        # For three-point: p0 = (3*p(1) - 3*p(2) + p(3))
        if len(scales) == 2:
            p_extrap = 2 * probs[0] - probs[1]
        else:
            p_extrap = 3 * probs[0] - 3 * probs[1] + probs[2]

        # Clip + renormalise (quasi-probs can go slightly negative)
        p_extrap = np.clip(p_extrap, 0, None)
        total = p_extrap.sum()
        if total == 0:
            # Degenerate: extrapolation collapsed to zero — fall back to uniform
            n_states = 2 ** run_result.num_qubits
            p_extrap = np.ones(n_states) / n_states
        else:
            p_extrap /= total

        n = run_result.num_qubits
        return {
            format(i, f"0{n}b"): float(p_extrap[i])
            for i in range(2 ** n)
            if p_extrap[i] > 0
        }


# =============================================================================
# No-op strategy
# =============================================================================

class NoMitigationStrategy(MitigationStrategy):
    """Pass-through: converts raw integer counts to float probabilities only."""

    def mitigate(
        self,
        run_result: RunResult,
        noise_model: NoiseModel,
    ) -> Dict[str, float]:
        total = sum(run_result.noisy_counts.values())
        return {k: v / total for k, v in run_result.noisy_counts.items()}


# =============================================================================
# Dispatcher
# =============================================================================

_REGISTRY: Dict[str, MitigationStrategy] = {
    "mem":  MEMStrategy(),
    "pec":  PECStrategy(),
    "none": NoMitigationStrategy(),
}


def get_strategy(name: str) -> MitigationStrategy:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown mitigation strategy '{name}'. Choose from: {list(_REGISTRY)}")
    return _REGISTRY[name]


def mitigate_run(
    run_result: RunResult,
    noise_model: NoiseModel,
) -> Dict[str, Dict[str, float]]:
    """
    Apply the configured mitigation layers and return a dict:
        {
          "mem": { bitstr: prob, ... },
          "pec": { bitstr: prob, ... } | None,
        }
    """
    mem_counts = get_strategy("mem").mitigate(run_result, noise_model)

    pec_counts = None
    if config.USE_PEC and run_result.name in config.PEC_CIRCUITS:
        pec_counts = get_strategy("pec").mitigate(run_result, noise_model)

    return {"mem": mem_counts, "pec": pec_counts}

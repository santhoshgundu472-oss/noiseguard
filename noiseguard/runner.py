"""
NoiseGuard — Runner
Executes each benchmark circuit under two conditions:
  1. Ideal (noiseless) — produces a Statevector for fidelity reference
  2. Noisy — produces counts via AerSimulator with the active noise model

Returns a RunResult per circuit consumed downstream by fidelity.py and mitigate.py.
"""
from dataclasses import dataclass, field
from typing import Dict

from qiskit import transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

from noiseguard import config
from noiseguard.circuits import BENCHMARK_CIRCUITS


@dataclass
class RunResult:
    name: str
    num_qubits: int
    ideal_sv: Statevector                   # noiseless reference
    noisy_counts: Dict[str, int]            # raw counts from noisy sim
    calibration_matrix: list = field(default_factory=list)  # filled by MEM


def run_all(noise_model: NoiseModel) -> list[RunResult]:
    """
    Run every circuit in BENCHMARK_CIRCUITS through:
      - noiseless Statevector simulator (ideal reference)
      - AerSimulator with noise_model (noisy counts)

    Returns a list of RunResult, one per circuit.
    """
    noisy_sim = AerSimulator(noise_model=noise_model)
    results = []

    for circuit_module in BENCHMARK_CIRCUITS:
        # --- Ideal statevector (no noise, no measurement) ---
        ideal_qc = circuit_module.ideal_statevector_circuit()
        ideal_sv = Statevector.from_instruction(ideal_qc)

        # --- Noisy counts ---
        noisy_qc = circuit_module.build()
        noisy_qc_t = transpile(noisy_qc, noisy_sim)
        job = noisy_sim.run(noisy_qc_t, shots=config.SHOTS)
        counts = job.result().get_counts()  # job is correct here — .run() returns a job

        results.append(RunResult(
            name=circuit_module.NAME,
            num_qubits=circuit_module.NUM_QUBITS,
            ideal_sv=ideal_sv,
            noisy_counts=counts,
        ))

    return results

"""
Exports the canonical list of benchmark circuit modules.
Each module exposes: build(), ideal_statevector_circuit(), NAME, NUM_QUBITS
"""
from noiseguard.circuits import bell_state, ghz_3qubit, qft_4qubit

BENCHMARK_CIRCUITS = [
    bell_state,
    ghz_3qubit,
    qft_4qubit,
]

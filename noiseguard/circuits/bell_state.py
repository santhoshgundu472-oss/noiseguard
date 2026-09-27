"""
Benchmark circuit 1 — Bell State (2 qubits)
Ideal output: |Φ+⟩ = (|00⟩ + |11⟩) / √2
Fidelity is highly sensitive to readout error and CX gate error.
"""
from qiskit import QuantumCircuit


def build() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc


def ideal_statevector_circuit() -> QuantumCircuit:
    """Same circuit without measurement — used for ideal SV simulation."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


NAME = "bell_state"
NUM_QUBITS = 2

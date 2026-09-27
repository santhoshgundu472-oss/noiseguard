"""
Benchmark circuit 2 — GHZ State (3 qubits)
Ideal output: |GHZ⟩ = (|000⟩ + |111⟩) / √2
More sensitive than Bell: two CX gates, three readout channels.
"""
from qiskit import QuantumCircuit


def build() -> QuantumCircuit:
    qc = QuantumCircuit(3, 3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.measure([0, 1, 2], [0, 1, 2])
    return qc


def ideal_statevector_circuit() -> QuantumCircuit:
    """Same circuit without measurement — used for ideal SV simulation."""
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    return qc


NAME = "ghz_3qubit"
NUM_QUBITS = 3

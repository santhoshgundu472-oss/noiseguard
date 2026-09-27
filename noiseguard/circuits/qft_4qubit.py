"""
Benchmark circuit 3 — Quantum Fourier Transform (4 qubits)
Deeper circuit with many single-qubit rotations and CX gates.
Most sensitive to gate errors — best candidate for PEC.
"""
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT


def build() -> QuantumCircuit:
    qc = QuantumCircuit(4, 4)
    # Initialise in |0101⟩ so QFT output is non-trivial
    qc.x(1)
    qc.x(3)
    qc.append(QFT(num_qubits=4, do_swaps=True), range(4))
    qc.measure(range(4), range(4))
    return qc


def ideal_statevector_circuit() -> QuantumCircuit:
    """Same circuit without measurement — used for ideal SV simulation."""
    qc = QuantumCircuit(4)
    qc.x(1)
    qc.x(3)
    qc.append(QFT(num_qubits=4, do_swaps=True), range(4))
    return qc


NAME = "qft_4qubit"
NUM_QUBITS = 4

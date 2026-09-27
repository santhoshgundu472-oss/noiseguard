"""
NoiseGuard — Noise Model
Builds a parameterized depolarizing noise model using rates from config.
Edit the rates in config.py — this file is what NoiseGuard watches for changes.
"""
from qiskit_aer.noise import (
    NoiseModel,
    depolarizing_error,
    ReadoutError,
)
from noiseguard import config


def build() -> NoiseModel:
    """
    Returns a NoiseModel with:
      - Depolarizing error on all single-qubit gates
      - Depolarizing error on CX (two-qubit gate)
      - Symmetric readout error on all qubits
    """
    model = NoiseModel()

    # Single-qubit gate depolarizing error
    sq_error = depolarizing_error(config.SINGLE_QUBIT_ERROR_RATE, 1)
    model.add_all_qubit_quantum_error(sq_error, ["h", "x", "rz", "sx", "u"])

    # Two-qubit gate depolarizing error
    tq_error = depolarizing_error(config.TWO_QUBIT_ERROR_RATE, 2)
    model.add_all_qubit_quantum_error(tq_error, ["cx"])

    # Symmetric readout (SPAM) error
    p = config.READOUT_ERROR_RATE
    ro_error = ReadoutError([[1 - p, p], [p, 1 - p]])
    model.add_all_qubit_readout_error(ro_error)

    return model

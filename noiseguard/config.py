# =============================================================================
# NoiseGuard — Central Configuration
# All tunables live here. Nothing else imports tunables from anywhere else.
# =============================================================================

# --- Simulation ---
SHOTS = 8192                        # shots per circuit run

# --- Regression thresholds ---
FIDELITY_DROP_THRESHOLD = 0.05      # global: flag if fidelity drops more than this

# Per-circuit overrides (circuit name → threshold). Falls back to global if absent.
PER_CIRCUIT_THRESHOLD = {
    "bell_state":  0.04,
    "ghz_3qubit":  0.06,
    "qft_4qubit":  0.07,            # deeper circuit → noisier → looser threshold
}

# --- Mitigation ---
MEM_ENABLED = True                  # always True — measurement error mitigation

USE_PEC = False                     # global PEC toggle
PEC_CIRCUITS = ["qft_4qubit"]       # circuits that get PEC when USE_PEC = True
PEC_SHOTS_MULTIPLIER = 10           # PEC needs more shots to control variance
PEC_NOISE_AMPLIFICATION_FACTORS = [1, 2, 3]  # Richardson extrapolation scale factors

# --- Noise model parameters (depolarizing) ---
SINGLE_QUBIT_ERROR_RATE = 0.001     # per single-qubit gate
TWO_QUBIT_ERROR_RATE    = 0.01      # per two-qubit gate
READOUT_ERROR_RATE      = 0.02      # per qubit per measurement

# --- Baseline ---
BASELINE_PATH = "baseline.json"

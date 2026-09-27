# NoiseGuard ⚡

> **Catch silent fidelity regressions in quantum noise models — automatically.**

Built for the **IBM Bob 2.0 Hackathon**.

---

## The Problem

When you edit a quantum noise model, the simulation can silently become
less realistic without throwing any error. Standard tests won't catch it —
the code still runs, results still look like numbers, but the fidelity has
quietly dropped. NoiseGuard catches that automatically, before it ships.

---

## How It Works

Every time you commit a change to the noise model, NoiseGuard:

1. Loads your noise model
2. Runs 3 benchmark circuits through it (Bell State, GHZ, QFT)
3. Applies **Measurement Error Mitigation (MEM)** to correct readout errors
4. Compares fidelity scores against a stored baseline
5. **Blocks the commit** if any circuit drops past its threshold

```
NoiseGuard Report  [MEM=ON  PEC=OFF]
────────────────────────────────────────────────────────────────────────────────────────────
Circuit             Raw Fid    MEM Fid    PEC Fid     Raw Δ     MEM Δ     PEC Δ  Status
────────────────────────────────────────────────────────────────────────────────────────────
bell_state           0.9773     0.9973      —       -0.0017   -0.0009      —     ✅ PASS
ghz_3qubit           0.9628     0.9926      —       -0.0037   -0.0042      —     ✅ PASS
qft_4qubit           0.9997     0.9996      —       -0.0001   -0.0001      —     ✅ PASS
────────────────────────────────────────────────────────────────────────────────────────────
RESULT: All circuits passed.
```

---

## Mitigation Layers

| Layer | What it fixes | Default |
|---|---|---|
| **MEM** — Measurement Error Mitigation | Readout / SPAM errors via calibration matrix inversion | Always ON |
| **PEC** — Probabilistic Error Cancellation | Gate errors via Richardson extrapolation to zero noise | Opt-in per circuit |

---

## Project Structure

```
noiseguard/
├── circuits/
│   ├── bell_state.py       # Benchmark 1 — 2-qubit Bell state
│   ├── ghz_3qubit.py       # Benchmark 2 — 3-qubit GHZ state
│   ├── qft_4qubit.py       # Benchmark 3 — 4-qubit QFT
│   └── __init__.py
│
├── watsonx/
│   ├── predictor.py        # Fidelity predictor (watsonx.ai or heuristic stub)
│   ├── explainer.py        # Plain-English regression explainer (foundation model or stub)
│   └── __init__.py
│
├── noise_model.py          # Depolarizing noise model (parameterized)
├── runner.py               # Runs circuits — ideal statevector + noisy counts
├── mitigate.py             # MEM and PEC strategy implementations
├── fidelity.py             # Classical fidelity (Bhattacharyya coefficient)
├── compare.py              # Diffs current scores vs baseline.json
├── report.py               # Formatted console output
├── config.py               # All tunables in one place
└── guard.py                # CLI entry point

baseline.json               # Stored ground-truth fidelity scores
.git/hooks/pre-commit       # Auto-runs on every git commit
```

---

## Requirements

- Python 3.10+
- [Qiskit](https://qiskit.org/) `>=1.0`
- [qiskit-aer](https://github.com/Qiskit/qiskit-aer) `>=0.14`
- numpy
- colorama *(optional — for coloured output)*

Install everything:

```bash
pip install qiskit qiskit-aer numpy colorama
```

---

## Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-username/noiseguard.git
cd noiseguard
pip install qiskit qiskit-aer numpy colorama
```

### 2. Make the pre-commit hook executable

```bash
chmod +x .git/hooks/pre-commit
```

### 3. Seed the baseline

Run this once after cloning, or whenever you intentionally update the noise model:

```bash
python3 -m noiseguard.guard --update-baseline
```

Output:
```
NoiseGuard: reseeding baseline...
Baseline saved to baseline.json

New baseline:
  bell_state        raw=0.9790  mem=0.9982  pec=—
  ghz_3qubit        raw=0.9665  mem=0.9969  pec=—
  qft_4qubit        raw=0.9998  mem=0.9997  pec=—
```

### 4. Run a check manually

```bash
python3 -m noiseguard.guard --run
```

### 5. From now on — just commit normally

```bash
git commit -m "your message"
# NoiseGuard runs automatically and blocks if fidelity regresses
```

To bypass during rapid iteration:

```bash
git commit --no-verify
```

---

## Configuration

All tunables live in [`noiseguard/config.py`](noiseguard/config.py) — nothing is buried elsewhere.

```python
# Simulation
SHOTS = 8192

# Regression thresholds
FIDELITY_DROP_THRESHOLD = 0.05          # global fallback
PER_CIRCUIT_THRESHOLD = {
    "bell_state":  0.04,
    "ghz_3qubit":  0.06,
    "qft_4qubit":  0.07,
}

# Mitigation
MEM_ENABLED = True
USE_PEC     = False                     # flip to True to enable PEC
PEC_CIRCUITS = ["qft_4qubit"]           # which circuits get PEC

# Noise model
SINGLE_QUBIT_ERROR_RATE = 0.001
TWO_QUBIT_ERROR_RATE    = 0.01
READOUT_ERROR_RATE      = 0.02
```

---

## Demonstrating a Regression

To see NoiseGuard catch a regression live:

1. Open `noiseguard/config.py` and change:
   ```python
   TWO_QUBIT_ERROR_RATE = 0.01   →   0.15
   ```

2. Run:
   ```bash
   python3 -m noiseguard.guard --run
   ```

3. You'll see:
   ```
   ghz_3qubit   0.8808   0.9112   —   -0.0857  -0.0856   —   🚨 FAIL
     ↳ MEM fidelity dropped -0.0856 (threshold -0.06)

   RESULT: 1 circuit(s) FAILED — noise model regression detected.
   ```

4. Restore the rate and re-run — all circuits pass again.

---

## Enabling PEC

In `config.py`:

```python
USE_PEC = True
PEC_CIRCUITS = ["qft_4qubit"]   # add more circuits as needed
```

Re-seed the baseline after enabling PEC so PEC fidelity scores are stored:

```bash
python3 -m noiseguard.guard --update-baseline
```

PEC uses Richardson extrapolation (noise scale factors `[1, 2, 3]`) to
estimate zero-noise fidelity. It requires ~10× more shots than MEM alone —
controlled by `PEC_SHOTS_MULTIPLIER` in config.

---

## Fidelity Metric

NoiseGuard uses **classical fidelity** (Bhattacharyya coefficient):

```
F = Σ √(p_ideal_i · p_measured_i)
```

This is the correct metric for shot-based simulation — it works for entangled
states (Bell, GHZ) where a density matrix comparison would give misleading
results (~0.5 regardless of noise level).

---

## IBM watsonx Integration

NoiseGuard includes a `--watsonx` mode that plugs into IBM watsonx.ai when
credentials are configured, and falls back transparently to a heuristic stub
when they are not — so the flag always works regardless of environment.

```bash
python3 -m noiseguard.guard --watsonx
```

Example output (stub mode):
```
NoiseGuard [watsonx mode — heuristic stub]
Noise parameters: SQ=0.001  TQ=0.01  RO=0.02

  bell_state        predicted=0.9900  baseline=0.9982  Δ=-0.0082  ✅ PASS
  [watsonx stub] bell_state: fidelity held at 0.9900 — no regression detected.

  ghz_3qubit        predicted=0.9900  baseline=0.9969  Δ=-0.0069  ✅ PASS
  ...

RESULT: All circuits passed watsonx prediction check.
```

### How to connect a real watsonx.ai deployment

Set two environment variables before running:

```bash
export WATSONX_API_KEY="your-api-key"
export WATSONX_PROJECT_ID="your-project-id"
```

Then point [`noiseguard/watsonx/predictor.py`](noiseguard/watsonx/predictor.py)
at your trained deployment — the `_predict_with_watsonx()` function has a
clearly marked `TODO` for this. Nothing else in the pipeline changes.

### watsonx v2 Roadmap

| Feature | File | Status |
|---|---|---|
| ML fidelity prediction (no simulation needed) | `watsonx/predictor.py` | Stub ready |
| Natural-language regression explanation | `watsonx/explainer.py` | Stub ready |
| Adaptive thresholds from run history | `watsonx/predictor.py` | Planned |
| watsonx.data fidelity history store | — | Planned |

---

## IBM watsonx Orchestrate — Workflow Design

Today, when NoiseGuard detects a regression it prints and exits — the developer
must manually decide what to do next. **watsonx Orchestrate** turns that single
detection event into a fully automated multi-skill workflow.

### The problem Orchestrate solves

Without Orchestrate, every regression requires 5 manual steps:
1. Read the console output
2. Decide: intentional change or bug?
3. Fix the noise model (or update the baseline)
4. Notify teammates
5. Open a tracking issue if needed

Orchestrate routes all of those steps automatically based on a single trigger.

### Proposed workflow

```
NoiseGuard detects regression
        │
        ▼
[Skill 1 — Explainer]
  Call watsonx.ai foundation model
  Generate plain-English root cause from circuit name, delta, noise params
        │
        ▼
[Skill 2 — Notifier]
  Post regression alert to Slack / email
  Include circuit name, fidelity delta, and explanation
        │
        ▼
[Skill 3 — Human Approval]  ← watsonx Orchestrate human-in-the-loop
  "Was this noise model change intentional?"
        │
        ├── Yes → [Skill 4 — Baseline Updater]
        │           Run --update-baseline automatically
        │           Commit new baseline.json to git
        │
        └── No  → [Skill 5 — Issue Creator]
                    Open GitHub issue with full regression report
                    Assign to noise model owner
        │
        ▼
[Skill 6 — Reporter]
  Post final summary to team dashboard
```

### Why this matters

| Without Orchestrate | With Orchestrate |
|---|---|
| Developer must manually act after every regression | Workflow runs automatically on detection |
| No team notification | Slack / email alert sent instantly |
| Developer decides intentional vs bug manually | Human-in-the-loop approval step built in |
| Baseline update requires manual CLI command | Auto-updated on approval |
| No issue tracking | GitHub issue created automatically on rejection |

### Skill definitions (ready to register in Orchestrate)

| Skill | Trigger | Action |
|---|---|---|
| `noiseguard_explain` | Regression detected | Call `watsonx/explainer.py` → return explanation string |
| `noiseguard_notify` | After explanation | POST to Slack webhook with formatted alert |
| `noiseguard_approve` | After notification | Present human approval prompt in Orchestrate UI |
| `noiseguard_update_baseline` | Approval = Yes | Shell: `python3 -m noiseguard.guard --update-baseline` |
| `noiseguard_open_issue` | Approval = No | POST to GitHub Issues API with regression report |
| `noiseguard_report` | After either branch | POST summary to team dashboard webhook |

This workflow is the natural v2 of NoiseGuard — the detection engine (v1,
built here) feeds directly into the Orchestrate workflow as its trigger event.

---

## Built With

- [Qiskit](https://qiskit.org/) — quantum circuit construction and simulation
- [Qiskit Aer](https://github.com/Qiskit/qiskit-aer) — noisy simulator backend
- [IBM watsonx.ai](https://www.ibm.com/watsonx) — fidelity prediction and regression explanation
- [IBM watsonx Orchestrate](https://www.ibm.com/products/watsonx-orchestrate) — automated post-regression workflow
- [IBM Bob 2.0](https://www.ibm.com/quantum) — hackathon platform

---

## License

MIT

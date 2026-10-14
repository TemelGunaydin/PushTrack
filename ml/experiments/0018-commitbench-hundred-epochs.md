# Experiment 0018: user-requested 100-epoch CommitBench run

Date: **2026-10-12**. **Stopped by the user, not completed or verified.** The user explicitly
requested 100 epochs after the completed three-epoch comparison and disclosure
of overfitting/worse validation results. This authorizes one new bounded
noncommercial research run, not automatic restarts, new data or product promotion.

## User-requested stop

At **20:32:38 UTC**, only the verified owned training and download process trees
were terminated. No artifacts were deleted. Native pause evidence at
`D:\PushTrackML\runs\user-pause-0001\report.json` observed **zero remaining owned
Python/inference workers** and the native sleep-inhibition controller exited.
The trainer's last report showed **epoch 72**, **71 fully measured epochs**,
**88,850 updates / 710,800 exposures**, and checkpoint directories 1–71 retained.
These are observed counters, not fresh independent training/checkpoint proof.
Completion verification did not run; there is no final epoch-100 checkpoint.
Original reports and frozen execution remain preserved, even where their
last historical status says running. This stop evidence supersedes that status.

Checkpoints save model/tokenizer, **not optimizer resume state**. Do not claim
exact optimizer/step resumption or automatically restart. See
[continuation notes](0019-local-subject-and-pause.md).

## Pinned recipe

- Same **10,000 complete original-source CommitBench training rows**, SHA-256
  `2840e70b84b9d8d3e26559724b83076e5c55e75701cdd9148cb1a9f103b151b2`.
- Same **962 development-validation rows**, SHA-256
  `76b9d83b60741738c29dc53f8629ec4c0e08434427595a5191682f19f42ba2ee`.
- Original verified CodeT5-small weights, SHA-256
  `968fb0f45e1efc8cf3dd50012d1f82ad82098107cbadde2c0fdd8e61bac02908`.
  **Not** a continuation of the previous adapted checkpoint or its optimizer.
- **100 complete epochs**, batch **8**, **1,250 updates/epoch**, **125,000 total
  updates / 1,000,000 repeated exposures**. Still only 10,000 unique examples.
- Shuffle seeds **42–141**; initial Torch seed 42. Max LR **5e-5**, AdamW
  decay .01/betas (.9,.999)/epsilon 1e-8, gradient clip 1, deterministic float32/
  eager CUDA. No AMP, quantization, LoRA, CPU fallback or package/model acquisition.
- **6,250 warmup updates** (five full epochs), followed by global linear decay.
  This rescaled schedule differs from the previous 3,750-update recipe; this is
  not an isolated extra-epoch effect or optimizer-state resume.
- Full train/validation losses and all 962 greedy validation generations after
  each epoch; same fixed 64 training-generation cases. Evaluation never backward
  or optimizer updates. Official **512 input / 64 target** limits, no truncation.
- Retain **all 100 epoch checkpoints**, approximately **24.2 GB** of weights.
  **Final epoch 100 selected before launch**, not retroactively replaced by a
  better earlier validation score. No metric-based early stop; no epoch 101.
- Existing finite loss/gradient and CUDA guards remain. A **20 GB disk reserve**
  plus next-checkpoint/log overhead is checked before training/saving each epoch.
  Errors stop safely, retain artifacts and never restart automatically.

All targets, source notices, quality holds and thirteen unapplied proposals
remain unchanged. False row/manifest quality and research-authorization flags
remain immutable; scoped user permission is separate in run/preflight evidence.
CommitBench remains **CC BY-NC 4.0**, separately from source MIT notices. Most
labels (9,960) are unreviewed. Fork/copy/privacy/pretraining clearance and CodeT5
product-distribution wording remain unresolved. The same validation is reused
development data, not a blind final test. No test access, new validation CSV,
Rust changes, deployment profiling, integration, commit or push.

## Preflight and actual launch evidence

**51 native Windows tests passed** with the executed source, including the
million-exposure plan, bounded 100-epoch/profile gates, global scheduler,
final-epoch selection, disk guard and preserved historical tests. The Chronicle
default still accepts only its original one-/three-/six-epoch recipes; CommitBench
accepts only separately authorized three-/100-epoch runs, never arbitrary counts.

Native preflight at **15:50:14.767172 UTC** passed: every 10,000/962 row loaded
with official lossless tokenization and pinned evidence; all hundred planned
epoch orders checked; **124 prior artifacts protected**. RTX 4070 observed
11.65 GB free GPU memory and 164.75 GB free disk. Previous training-0005 model,
report, proof and reviews remain preserved.

Retained-SSH controller launched at **15:57:43.6194365 UTC**. Windows launcher
PID **22076**, native Python child **26928** (one logical run, not two models).
The first live observation showed `status: running`, `stage: baseline`, planned
125,000 updates and 6,250 warmup; **zero completed updates at that observation**.
That is launch evidence, not a completed-training/reload or quality claim.
A later live snapshot confirmed **epoch 1's 1,250 training updates / 10,000
exposures**, with its validation measurement in progress. Read-only checks
reconfirmed all 124 prior artifacts and the frozen execution hashes unchanged.
These partial observations do not verify all hundred epochs.

Execution uses an owned frozen source bundle at
`D:\PushTrackML\runs\training-execution-0006\`, isolated from later edits to the
mutable `experiment\` helpers. The SSH controller has keepalives and a **24-hour
training deadline** (not an extension of the 100-epoch budget); on timeout it
terminates only its owned process tree and preserves partial evidence. No
service, scheduled task or reconnect/restart loop.

Mac `caffeinate` and a process-scoped native Windows system-sleep request protect
the retained SSH/job lifetime. No permanent power-plan/display configuration is
changed; inhibition ends with the controller. Manual sleep/shutdown, network
loss or resource failures can still interrupt the run. Historical timing suggests
roughly **seven hours**, not a measured completion guarantee.

## Pending completion checks

After a successful training exit, the frozen controller invokes a fresh native
verifier once, without optimizer updates. It is intended to verify all 125,000
step orders/LRs, every identity's 100 exposures, all 100 checkpoint hashes,
all per-epoch loss/generation identity accounting, original baseline reproduction,
final-epoch selection and a fresh final reload's 16 predictions/two batch losses.
This verification **has not yet run**. Its result must be observed, not assumed.

The verifier then freezes the same twenty development cases alongside the old
Chronicle/CommitBench three-epoch predictions. Semantic review remains manual,
unblinded development evidence and **pending**, not automated accuracy or a
promotion rule. No outcomes are replaced. A verifier failure preserves evidence
and never retrains or blindly reruns output writers.

## Artifact locations

- Run: `D:\PushTrackML\runs\training-0006\`.
- Controller: `runs\training-controller-0006.json`.
- Permission/preflight: `runs\training-preflight-0006.json` and its retained source.
- Frozen execution: `runs\training-execution-0006\`.
- Training logs: `runs\training-0006.stdout.log` / `.stderr.log`.
- Native test logs: `runs\training-0006.tests.stdout.log` / `.stderr.log`.
- Future proof logs: `runs\training-0006.verification.stdout.log` / `.stderr.log`.
- Mac retained controller PID **82291**, `/tmp/pushtrack-hundred-control.log`.

| Frozen executed artifact | SHA-256 |
| --- | --- |
| Trainer | `fd4f2664fdbd6b91dbc677ad79125baaf0f2dbb268f28bbb2a6f246c1f2803cf` |
| Alternate-loader/recipe tests | `2baa95239040a4f4de2173e314618c2260905923a949e9bf2b0658b3f3eff12c` |
| Pending completion verifier | `7e643920bbf5c5d872eb62df1125b7ee7a29f7a939a40a13a6662960916be029` |

Do not report all 100 epochs, a final reload or improved semantic quality until
actual completion evidence is available. The prior
[three-epoch report](0017-commitbench-training.md) remains the latest completed
CommitBench model result.

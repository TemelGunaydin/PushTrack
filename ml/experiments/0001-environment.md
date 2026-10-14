# Experiment 0001: native Windows CUDA environment

Date: 2026-10-03. This is a setup experiment, not model training.

## Question

Can the existing Windows machine execute verified CUDA forward and backward
operations in an isolated Python environment, without Ubuntu or cloud compute?

## Observed setup

- Native Windows 11 Pro, version 26H2, build 26300.9457.
- NVIDIA GeForce RTX 4070, 12,282 MiB reported VRAM; driver 616.92.
- 63.8 GiB system RAM.
- Existing CPython 3.12.8 x64; uv 0.12.17.
- Dedicated workspace: `D:\PushTrackML`, outside OneDrive and the repository.
- PyTorch `2.14.1+cu130`, bundled CUDA runtime `13.0`.
- Ten packages pinned in `requirements-windows.lock` with SHA-256 hashes;
  official PyTorch CUDA index, binary packages only.
- D: free space: approximately 177.1 GiB before setup, 174.2 GiB afterward.
  This difference is a workspace/storage observation, not model artifact size.

The WinGet uv symbolic link did not execute over SSH. Resolving its real binary
worked; no global PATH or package-manager configuration was changed. Multiple
Python executables were on PATH; setup selects the first application and verifies
it is 64-bit Python 3.12 rather than modifying the other installations.

## Proof

`check_environment.py` ran successfully on 2026-10-03 at 18:00:04 UTC:

- Device: RTX 4070; compute capability 8.9.
- GPU-reported total memory: 12,878,086,144 bytes.
- Forward: CUDA multiplication of two 256 x 256 all-ones float32 matrices;
  every resulting value was exactly 256.
- Backward: gradient of the summed result with respect to the shared input;
  every gradient value was exactly 512.
- Both assertions passed; process exited with code 0.
- Peak PyTorch CUDA tensor allocation for this test: 18,351,104 bytes (17.5 MiB).
  This excludes driver/context memory and says nothing about model inference
  RAM, end-user requirements, training VRAM, or generation performance.

Full runtime proof is local at `D:\PushTrackML\runs\environment-first.json`.
NumPy was deliberately not installed; torch emitted a missing-NumPy warning,
without affecting these native tensor checks.

## Additional verification

- Setup rerun consumed the existing lock, checked all ten packages, and succeeded
  without downloading or replacing the environment.
- Process-local uv and temporary-directory variables were restored after setup.
- CUDA forward/backward proof passed again at 18:08:39 UTC.
- With `CUDA_VISIBLE_DEVICES=-1` temporarily set for the check process, the
  script exited with code 1 and reported that no CPU fallback was used. The
  original visibility setting was restored afterward.
- SHA-256 hashes of the setup script, GPU check, input requirements, and lock
  matched between the repository and Windows copies.
- Python syntax/help checks passed. The illustrative JSON parsed successfully,
  and its patch passed `git apply --check` in a temporary synthetic repository.
- Git ignore checks covered environments, caches, datasets, run reports,
  checkpoints, and exports. No Rust source or Cargo file changed.

## Scope and conclusion

The machine can execute CUDA tensor operations and compute gradients natively
on Windows. No model or dataset was downloaded, no training or fine-tuning ran,
and no CUDA toolkit, Ubuntu distribution, or global Python packages were installed.
PushTrack's Rust code and folder configuration were not changed.

Next: a small, reviewed diff/message dataset and a documented model-license
selection. This experiment does not prove commit-message quality or low-RAM
CPU deployment.

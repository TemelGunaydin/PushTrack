"""Verify CUDA forward/backward operations without loading or training a model."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Save the JSON proof outside source control.")
    args = parser.parse_args()

    try:
        import torch
    except ImportError as error:
        parser.exit(1, f"PyTorch cannot be imported: {error}. Run setup-windows.ps1 first.\n")

    if not torch.cuda.is_available():
        parser.exit(1, "CUDA is not available. No CPU fallback was used.\n")

    torch.cuda.init()
    torch.cuda.reset_peak_memory_stats()
    size = 256
    x = torch.ones((size, size), dtype=torch.float32, device="cuda", requires_grad=True)
    result = x @ x
    # Exact integer-valued results avoid a platform-dependent tolerance threshold.
    torch.testing.assert_close(result, torch.full_like(result, size), rtol=0, atol=0)
    result.sum().backward()
    torch.testing.assert_close(x.grad, torch.full_like(x, 2 * size), rtol=0, atol=0)
    torch.cuda.synchronize()

    device = torch.cuda.get_device_properties(0)
    report = {
        "recorded_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "purpose": "environment proof; not model training or an inference benchmark",
        "platform": platform.system(),
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "cuda_runtime": torch.version.cuda,
        "gpu": device.name,
        "compute_capability": f"{device.major}.{device.minor}",
        "gpu_total_bytes": device.total_memory,
        "matrix_size": [size, size],
        "forward": "pass",
        "backward": "pass",
        "test_peak_gpu_allocated_bytes": torch.cuda.max_memory_allocated(),
    }
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

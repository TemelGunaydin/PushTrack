"""Tokenizer-only fidelity experiment on the existing pilot; never loads weights."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

from tokenizers import AddedToken, Tokenizer, decoders, models, pre_tokenizers, processors

from prepare_pilot import Network, PREFIX, TOKENIZER_HASH, TOKENIZER_REVISION, digest, json_write

# Immutable Hugging Face revisions and Git blob hashes from the model-tree API.
# This allowlist contains only tokenizer assets/cards/configs, never model weights.
CANDIDATES = {
    "codet5-small": {
        "repo": "Salesforce/codet5-small",
        "revision": "b1ee9570c289f21b5922b9c768a1ce12957bf968",
        "files": {
            "README.md": (4603, "7ca1a7ffde02e3739be08e0b063d2f7d585df15a"),
            "config.json": (1566, "056c085b0bf1966a4658710891af6de209b608be"),
            "tokenizer_config.json": (1477, "263a6f72aceb1716442638a3bcf20afe1eb0de9a"),
            "special_tokens_map.json": (12512, "e830a2bc8cae841f929043d588e1edcffb28fe9a"),
            "added_tokens.json": (2, "9e26dfeeb6e641a33dae4961196235bdb965b21b"),
            "vocab.json": (703051, "38ed64670805e4a3ff4cfa6f764629324a4e3c1e"),
            "merges.txt": (294364, "319fd0bbb49414442ca8c66a675ebce7b3fec747"),
        },
    },
    "bart-base": {
        "repo": "facebook/bart-base",
        "revision": "aadd2ab0ae0c8268c7c9693540e9904811f36177",
        "files": {
            "README.md": (2593, "be4dfed9842f07141364914615f4a8238973fd4d"),
            "config.json": (1716, "7c84a2e277097ae01ff7ecc03d977a930b713058"),
            "tokenizer.json": (1355863, "ad0bcbeb288f0d1373d88e0762e66357f55b8311"),
        },
    },
    "smollm2-135m": {
        "repo": "HuggingFaceTB/SmolLM2-135M",
        "revision": "93efa2f097d58c2a74874c7e644dbc9b0cee75a2",
        "files": {
            "README.md": (6340, "4049f762cb41ec6f526936c9af80ae216048bc74"),
            "config.json": (704, "ccf3dac2f33905d152adbdf3886b5e38a4eb7579"),
            "tokenizer_config.json": (3658, "d45192775d58298087a1fedf5967fe5b63b091ab"),
            "tokenizer.json": (2104556, "f922b1797f0c88e71addc8393787831f2477a4bd"),
        },
    },
}
SYNTHETIC = {
    "punctuation": 'if (a < b && ready) { map["key"] = x ^ y; }\n',
    "indentation": 'def f(x):\n\tif x:\n        return 1\n\n    return 0\n',
    "crlf": 'a = 1\r\n\tb = 2\r\n',
    "unicode": 'const café = "İstanbul 中文 🙂";\n',
    "whitespace": '  one  two\tthree\n\nend  \n',
    "literal_specials": 'text = "  <mask> <extra_id_0> <|im_start|>"\n',
}


def verify_asset(data: bytes, size: int, blob: str) -> str:
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if len(data) != size or actual != blob:
        raise ValueError("Pinned tokenizer artifact integrity check failed")
    return digest(data)


def load_codet5(directory: Path) -> Tokenizer:
    """Reconstruct its RoBERTa backend from checkpoint-owned assets, not new merges."""
    config = json.loads((directory / "tokenizer_config.json").read_text())
    special = json.loads((directory / "special_tokens_map.json").read_text())
    if json.loads((directory / "added_tokens.json").read_text()) != {}:
        raise ValueError("Unexpected added vocabulary; reconstruction needs explicit review")
    backend = Tokenizer(models.BPE.from_file(
        str(directory / "vocab.json"), str(directory / "merges.txt"), unk_token="<unk>"
    ))
    backend.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=config["add_prefix_space"])
    backend.decoder = decoders.ByteLevel()
    unique = {}
    for entry in special.values():
        for item in (entry if isinstance(entry, list) else [entry]):
            unique[item["content"]] = item
    original_size = backend.get_vocab_size()
    backend.add_special_tokens([AddedToken(**value, special=True) for value in unique.values()])
    if backend.get_vocab_size() != original_size:
        raise ValueError("Special-token registration changed pretrained vocabulary IDs")
    bos = backend.token_to_id(special["bos_token"]["content"])
    eos = backend.token_to_id(special["eos_token"]["content"])
    backend.post_processor = processors.RobertaProcessing(
        (special["eos_token"]["content"], eos),
        (special["bos_token"]["content"], bos),
        add_prefix_space=config["add_prefix_space"],
    )
    model_config = json.loads((directory / "config.json").read_text())
    if (bos, eos, backend.get_vocab_size()) != (
        model_config["bos_token_id"], model_config["eos_token_id"], model_config["vocab_size"]
    ):
        raise ValueError("Reconstructed backend does not match checkpoint special IDs/vocabulary")
    return backend


def measure(backend: Tokenizer, text: str, unknown_token: str) -> dict:
    # Raw round-trip excludes inserted BOS/EOS but retains any literal special tokens.
    # No Transformers cleanup, padding, truncation, or special-token escaping is applied.
    raw = backend.encode(text, add_special_tokens=False)
    decoded = backend.decode(raw.ids, skip_special_tokens=False)
    unknown_id = backend.token_to_id(unknown_token)
    return {
        "tokens_with_specials": len(backend.encode(text, add_special_tokens=True).ids),
        "unknown_id_occurrences": raw.ids.count(unknown_id) if unknown_id is not None else 0,
        "exact_roundtrip": decoded == text,
        "newlines_preserved": decoded.count("\n") == text.count("\n"),
        "tabs_preserved": decoded.count("\t") == text.count("\t"),
        "input_characters": len(text),
        "decoded_characters": len(decoded),
    }


def compare(backend: Tokenizer, rows: list[dict], unknown: str) -> dict:
    backend.no_padding()
    backend.no_truncation()
    observations = []
    for row in rows:
        input_stats = measure(backend, PREFIX + row["diff"], unknown)
        target_stats = measure(backend, row["message"], unknown)
        observations.append({
            "diff_sha256": row["diff_sha256"], "split": row["split"],
            "input": input_stats, "target": target_stats,
            "within_pilot_budget": input_stats["tokens_with_specials"] <= 512 and target_stats["tokens_with_specials"] <= 64,
        })
    lengths = [r["input"]["tokens_with_specials"] for r in observations]
    return {
        "vocabulary_size": backend.get_vocab_size(), "examples": len(rows),
        "input_tokens_total": sum(lengths), "input_tokens_min": min(lengths), "input_tokens_max": max(lengths),
        "unknown_input_id_occurrences": sum(r["input"]["unknown_id_occurrences"] for r in observations),
        "exact_input_roundtrips": sum(r["input"]["exact_roundtrip"] for r in observations),
        "exact_target_roundtrips": sum(r["target"]["exact_roundtrip"] for r in observations),
        "within_512_input_64_target": sum(r["within_pilot_budget"] for r in observations),
        "observations": observations,
        "synthetic": {name: measure(backend, text, unknown) for name, text in SYNTHETIC.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New report/artifact directory, never overwritten.")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the previous experiment")
    queue = args.pilot / "review-pending.jsonl"
    if queue.stat().st_size > 1_000_000:
        parser.error("Pilot queue exceeds the bounded experiment size")
    original = queue.read_bytes()
    rows = [json.loads(line) for line in original.splitlines()]
    if not 1 <= len(rows) <= 24 or any(row["review_status"] != "pending" for row in rows):
        parser.error("Expected 1-24 review-pending examples; no approval/status changes are made")
    if any(digest(row["diff"].encode()) != row["diff_sha256"] for row in rows):
        parser.error("Pilot diff integrity check failed")
    baseline_file = args.pilot / "tokenizer.json"
    if digest(baseline_file.read_bytes()) != TOKENIZER_HASH:
        parser.error("T5 baseline tokenizer integrity check failed")
    args.output.mkdir(parents=True)
    network = Network(budget=6_000_000)
    report = {
        "status": "running", "started_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "platform": platform.system(), "python": platform.python_version(),
        "tokenizers_version": importlib.metadata.version("tokenizers"),
        "script_sha256": digest(Path(__file__).read_bytes()), "queue_sha256": digest(original),
        "purpose": "encoding fidelity, not commit quality, inference RAM, or model selection",
        "input_prefix": PREFIX, "training_approved": 0, "weights_downloaded": False,
        "artifacts": {}, "results": {},
    }
    try:
        report["results"]["t5-small"] = compare(Tokenizer.from_file(str(baseline_file)), rows, "<unk>")
        report["artifacts"]["t5-small"] = {"revision": TOKENIZER_REVISION, "tokenizer_sha256": TOKENIZER_HASH, "reused": True}
        for name, candidate in CANDIDATES.items():
            directory = args.output / name
            directory.mkdir()
            files = {}
            for filename, (size, blob) in candidate["files"].items():
                path = directory / filename
                url = f'https://huggingface.co/{candidate["repo"]}/resolve/{candidate["revision"]}/{filename}'
                network.fetch(url, size, path)
                files[filename] = {"bytes": size, "git_blob_sha1": blob, "sha256": verify_asset(path.read_bytes(), size, blob)}
            report["artifacts"][name] = {"repo": candidate["repo"], "revision": candidate["revision"], "files": files}
            backend = load_codet5(directory) if name == "codet5-small" else Tokenizer.from_file(str(directory / "tokenizer.json"))
            unknown = "<|endoftext|>" if name == "smollm2-135m" else "<unk>"
            report["results"][name] = compare(backend, rows, unknown)
        # Reference only: UTF-8 length plus one EOS, not a loaded ByT5 tokenizer/model.
        byte_lengths = [len((PREFIX + r["diff"]).encode("utf-8")) + 1 for r in rows]
        report["raw_byte_reference"] = {"input_min_plus_eos": min(byte_lengths), "input_max_plus_eos": max(byte_lengths), "inputs_within_512": sum(n <= 512 for n in byte_lengths)}
        if queue.read_bytes() != original:
            raise ValueError("Pilot changed while comparison was running")
        report["status"] = "complete"
    except Exception as error:
        report["status"] = "stopped"
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        report["response_body_bytes"] = network.received
        report["network_requests"] = network.requests
        report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
        json_write(args.output / "report.json", report)
        summary = {**report, "results": {name: {k: v for k, v in result.items() if k != "observations"} for name, result in report["results"].items()}}
        print(json.dumps(summary, indent=2))
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())

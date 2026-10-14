# Experiment 0003: tokenizer fidelity before model selection

Completed on native Windows: **2026-10-05, 08:21:58-08:22:04 UTC**.
No weights, training, new corpus acquisition, new dependencies, or data approval.

## Question and method

Can a compact-model tokenizer preserve code punctuation and whitespace while
fitting the proposed input budget? This is **not** a model-quality or RAM test.

`compare_tokenizers.py` used the existing nine review-pending examples in
`D:\PushTrackML\data\pilot-0001` and six synthetic diagnostic strings. The
unchanged data environment used Python 3.12.8 and tokenizers 0.23.2. Tokenization
and artifact downloads ran only on Windows; no corpus was copied into Git.

Each input was the same `summarize changes: ` prefix plus the complete diff.
Lengths include backend-inserted special tokens. Fidelity means exact string
recovery after encoding **without inserted special tokens** and decoding with
`skip_special_tokens=False`. No padding, truncation, cleanup, or escaping was
applied. Unknown-ID occurrences exclude automatically inserted special tokens.
A literal unknown/special marker can itself encode as a reserved ID, so this
metric alone is not a universal out-of-vocabulary detector.

## Measured results on the nine existing examples

| Tokenizer | Total input tokens | Range | Unknown IDs | Exact input round-trips | Fits 512 input / 64 target |
| --- | ---: | ---: | ---: | ---: | ---: |
| T5-small | 3,252 | 187-486 | 68 | 0/9 | 9/9 |
| CodeT5-small | 2,644 | 163-389 | 0 | 9/9 | 9/9 |
| BART-base | 3,275 | 179-608 | 0 | 9/9 | 8/9 |
| SmolLM2-135M | 2,756 | 171-404 | 0 | 9/9 | 9/9 |

All four preserved all nine target subjects exactly. CodeT5 used approximately
18.7% fewer input tokens than T5 on this set. This is not a measured latency,
training-cost, quality, or memory improvement. T5's lower counts in some cases
also reflect destructive normalization; shorter is not automatically better.

The pilot was already filtered using T5 token lengths, and contains only nine
examples with unresolved data reviews. It is biased and far too small to rank
commit-message quality or establish general token-budget acceptance rates.
Three examples belong to validation, but no model predictions or test data
were inspected. SmolLM2 is decoder-only: its eventual training prompt, target,
EOS, loss masking, and combined context budget differ from encoder-decoder
models. The shared prefix here is for measurement consistency, not its final
fine-tuning protocol. The 512-token threshold is our pilot policy, not a claim
about every candidate model's native maximum context.

## Synthetic diagnostics: zero unknowns is not enough

Synthetic strings exercise punctuation, indentation, CRLF, Unicode, repeated
whitespace, and literal special-marker text.

- T5 failed all six exact round-trips. Even when no unknown ID appeared,
  line breaks and indentation could disappear.
- CodeT5 and BART preserved the first five exactly but lost whitespace around
  literal `<mask>`/sentinel-like content in the sixth. Their special-token
  matching rules can absorb adjacent spaces.
- SmolLM2 preserved all six exactly, including the marker-string fixture.
  However, round-trip fidelity does not mean embedded markers are encoded as
  ordinary text rather than reserved/control IDs. A literal-special-token
  policy remains necessary for every model before training/integration.

No escaping or tokenizer changes were implemented in this experiment. Do not
swap a tokenizer into unrelated pretrained weights: IDs and embeddings must
match. Do not silently normalize away source characters to improve this score.

A raw UTF-8 byte-count reference (prefix + diff + one EOS) ranged from 450 to
1,347, with only 2/9 within 512. This is **not** a ByT5 tokenizer/model execution.
Published ByT5-small is approximately 300M parameters, so both parameter count
and longer sequences make it less attractive for our initial low-RAM goal.

## Artifacts and implementation fidelity

Exact revisions:

| Repository | Revision |
| --- | --- |
| `google-t5/t5-small` | `df1b051c49625cf57a3d0d8d3863ed4d13564fe4` |
| `Salesforce/codet5-small` | `b1ee9570c289f21b5922b9c768a1ce12957bf968` |
| `facebook/bart-base` | `aadd2ab0ae0c8268c7c9693540e9904811f36177` |
| `HuggingFaceTB/SmolLM2-135M` | `93efa2f097d58c2a74874c7e644dbc9b0cee75a2` |

T5 reused its already-pinned local JSON. BART and SmolLM2 loaded their own
published tokenizer JSONs directly. CodeT5 has vocabulary/merges/config files,
not a tokenizer JSON: its RoBERTa-style Rust backend was reconstructed from
those exact assets, including all special-token descriptors and BOS/EOS rules.
Vocabulary size and special IDs matched the checkpoint config. No vocabulary
was trained or augmented. This backend has **not** been checked for complete
ID-by-ID parity with the upstream Transformers Python reference; do that before
using it in training, particularly for reserved-marker edge cases.

The successful run fetched 14 allowlisted card/config/tokenizer files totaling
**4,493,005 response-body bytes**. Git blob IDs and sizes were pinned before
fetching; SHA-256 values were recorded afterward. No glob-based repository
snapshot, model `.bin`/`.safetensors`, or executable remote code was downloaded.

The first attempt stopped after 1,017,575 bytes because tokenizers 0.23.2 did
not accept a named `cls` argument in `RobertaProcessing`. The constructor call
was corrected to positional arguments and a reconstruction regression test
was added. The stopped report/source remain in `runs\tokenizer-0001`; the
successful run is `runs\tokenizer-0002`. Combined tokenizer-run response bodies
were **5,510,580 bytes**; no dataset shard was downloaded again.

## Licenses and recommendation

Primary cards, at the revisions above:

- [CodeT5-small](https://huggingface.co/Salesforce/codet5-small/blob/b1ee9570c289f21b5922b9c768a1ce12957bf968/README.md):
  Apache-2.0 metadata, but the card also says **research purposes only** and
  references Salesforce policies. Its approximately 60M-parameter model is the
  closest technical match to the original small-model goal. Treat the conflicting
  wording as unresolved for product distribution; this tokenizer-only research
  does not settle that question. The implementation's open-source license does
  not automatically establish the license for vocabulary/merge assets.
- [BART-base](https://huggingface.co/facebook/bart-base/blob/aadd2ab0ae0c8268c7c9693540e9904811f36177/README.md):
  Apache-2.0 Hub metadata, approximately 139M parameters, encoder-decoder. The
  HF-authored card does not contain the Salesforce research-only statement.
  It is a general-text model, and one pilot input exceeded our 512-token budget.
- [SmolLM2-135M](https://huggingface.co/HuggingFaceTB/SmolLM2-135M/blob/93efa2f097d58c2a74874c7e644dbc9b0cee75a2/README.md):
  explicit Apache-2.0 license section, published approximately 135M parameters,
  decoder-only architecture, and some code pretraining. It is the stronger
  clearly documented fallback here, but exceeds our initial 60-100M size target.
- [ByT5](https://github.com/google-research/byt5): raw-byte alternative reviewed
  from documentation only; not selected or downloaded.

**Recommendation:** keep CodeT5-small as the technical research favorite for
minimal parameter count, with its distribution-license question unresolved.
Keep SmolLM2-135M as the fallback if license clarity is prioritized. Neither is
approved or downloaded as a model. BART offers no compelling advantage in this
small fidelity check to justify its larger size and token-budget miss.

Published parameter counts are not measurements of runtime RAM. Roughly 60M
versus 135M parameters means different raw weight sizes, not a promise of a
specific INT8 artifact, CPU latency, peak RAM, or quality. Those require actual
later experiments. The license assessment is documentation review, not legal
clearance, and source-data permissions remain a separate gate.

## Verification and next gate

- **30 tests passed on Windows:** 9 tokenizer checks plus the 21 pilot checks.
- All four real-example and synthetic measurements reproduced **exactly offline**
  with network access disabled in the replay path.
- All downloaded asset hashes matched; no extra/weight files were present.
- Existing-output refusal returned exit 2 and preserved the report.
- Original pilot report and pending-queue hashes were unchanged.
- No Rust source, CUDA dependencies, training approvals, commits, or pushes changed.

Successful local report:
`D:\PushTrackML\runs\tokenizer-0002\report.json`.
Report SHA-256:
`8aec8f68d3c57a7285f41c13979f1e258b97f9598c65cd510293b6feb590e2af`.
Script SHA-256:
`0e091a8cb76ddf20a74686b2b92cc38d7c884c796b94a03280b5a64148ed709e`.

Before training: choose the research/model-license path explicitly, check
reference-tokenizer parity and literal-special handling, and expand/review the
existing pilot without repeating shard downloads. No candidate should be
called production-ready on the basis of these nine encoding examples.

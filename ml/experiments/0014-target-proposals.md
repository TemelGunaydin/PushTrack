# Experiment 0014: traceable training-target proposals

Date: 2026-10-11. **Proposal and mechanical verification completed; not applied.**
The user approved target-quality work after the bounded six-epoch comparison
and asked whether alternative data could help. Dataset options are documented
separately in [data-improvement-options.md](../research/data-improvement-options.md).

## Scope

Use the existing frozen **9,758-row training set** and the 24 training-only
examples already read in full in experiment 0012. Do not consult validation
outputs to choose corrections, rewrite originals, exclude rows automatically,
or create a new training export yet. All real data/tokenizer processing runs
natively on Windows in the existing data environment.

The one-off `propose_targets.py` helper has no apply or training operation.
Its executed source and `test_propose_targets.py` are retained under the Windows
experiment's `provenance/`, not in Git: the helper includes the real draft
annotations. It verifies the frozen training hash, identities, split/quality
flags and diff hashes. Proposed targets
are checked with the pinned official tokenizer and lossless **512 input / 64
target token** limits, plus a single-line 72-character limit. No trimming,
truncation, special-marker escaping, or label mutation is performed.

## Nine proposals, not nine proven bad labels

Original subjects and full source records remain untouched. Proposals carry
repository/commit identity, original subject, diff hash, zero-based row index,
new text, evidence, issue kind, token counts and reviewer identity. Every proposal
is marked `proposed_not_approved`; none is independent human annotation.

| Commit prefix | Kind | Proposed target |
| --- | --- | --- |
| `3dd33bc7c842` | Factual correction | Remove the CI post-server delay and asset fetch |
| `c7884d1c5a7b` | Factual correction | Use testnet instead of simnet in the Docker faucet example |
| `ad5feb7e92eb` | Ambiguity clarification | Remove the comments about returning default values |
| `75e440686be4` | Coverage clarification | Replace SQLite's reverse function with comma splitting |
| `cf434cad2dce` | Visible-change clarification | Only include answer spans when FastQA inputs have answers |
| `c9ae1ccfb324` | Optional specificity | Document the Visual C++ runtime requirement for Windows builds |
| `9d53211a91fd` | Optional specificity | Replace imui with messagelist in Android sample Gradle references |
| `5c04b868b0ec` | Optional specificity | Remove DataSetExtensions and Microsoft.CSharp references from DSAHelper |
| `4eb841466882` | Optional specificity | Set a dynamic camera target after clearing focus in the story handler |

The first target replaces the contradicted **add composer install** label; the
patch only removes the post-server sleep and asset fetch, while an earlier wait
remains. The second corrects **simtest** to the actual replaced value **simnet**.
The next three remove ambiguity, omitted replacement behavior, or an unverifiable
test-failure claim. The final four original subjects are supported but generic;
those proposals are optional enrichment, not corrections of proven falsehoods.

Only nine targets are proposed. This small cleanup is not expected by itself
to solve all model grounding/capacity/generalization problems, and no model
quality gain is claimed without a future controlled run.

## Full-set mechanical screen

All 9,758 rows were screened with declared conservative heuristics:

| Flag | Hits |
| --- | ---: |
| Text/comment-like change without explicit text scope in the subject | 345 |
| Removal-worded subject on additions-only nonblank hunks | 28 |
| Addition-worded subject on removals-only nonblank hunks | 3 |
| Very generic exact subject pattern | 0 |

There are **373 unique flagged records**, with overlapping reasons. They are
**inspection leads, not 373 incorrect labels**. Removing a guard can add support;
adding configuration can disable behavior; a README badge addition can have a
perfectly good title without saying README. Comment syntax can affect tooling,
and this heuristic misses some inline/multiline cases. It is not a parser-based
semantic classifier. No flags automatically rewrite, approve or exclude rows.

## Validation and artifacts

- **10 focused tests passed** on native Windows, covering frozen data/flags,
  duplicate/unknown identities, original-label drift, source preservation,
  target text/token limits, explicit evidence, hunk/header parsing, direction
  flags and comment/preprocessor/shebang distinctions.
- Initial proof passed at **15:42:36 UTC**: all nine proposals fit official
  tokenizer budgets; **55 protected input artifacts** stayed unchanged.
- A fresh process independently verified all nine source/target identities and
  token counts, all 373 flag identities/counts, and 51 prior protected artifact
  hashes plus pinned current review evidence at **15:47:25 UTC**. This is a
  mechanical second-process check, not independent semantic annotation.
- **9,758 rows retained; zero targets changed; zero optimizer updates.** No
  validation/test records were used as correction candidates. No corpus/model
  downloads, GitHub metadata sweep, package installation or app changes occurred.

Artifacts: `D:\PushTrackML\runs\target-proposal-0001\`:

- `proposal.json`, `flagged-candidates.json`, `verification.json`.
- `independent-verification.json`, `provenance/`.

Hashes:

| Artifact | SHA-256 |
| --- | --- |
| Frozen training data | `5dd4d286b73bea89456bdb2cb3c5cb23a3757ad38a6baaa37099fe5f0a4d4269` |
| Proposed targets | `73bf84f1fba4beb936001581e04eb66f684b9c780c1f7df092ae9a6d3edbbe7a` |
| Flagged candidates | `0403cdbd864cc4c94ca46a775ee90bc80af2815210f1a7696042b6bcb1aa0583` |
| Fresh verifier | `8fc89e49964021c112fe5cb0a8e0c645f298e30852fbb875446a1f371ad738ed` |

## Decision boundary

Applying an overlay, changing the training loader/data version, and retraining
require a separately declared recipe and approval. Preserve the entire eligible
training set; the reviewed examples are not a replacement training subset.
Any future data expansion must keep independent validation/test boundaries,
original complete diffs, provenance and license/privacy checks intact. A larger
or differently named dataset does not automatically meet those conditions.

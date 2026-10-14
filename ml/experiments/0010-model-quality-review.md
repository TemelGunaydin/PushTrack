# Experiment 0010: twenty diff-grounded model-output reviews

Date: 2026-10-05. Completed at **18:00:21.868704 UTC**. **Assistant judgment:
3 usable subjects, 12 needing edits, 5 misleading**, among the 20 selected final
outputs. All 20 corresponding pretrained-baseline outputs were non-subject
fragments. These are sample counts, **not a population accuracy estimate** or
independent human annotation. The model is not ready for unattended publishing.

Subsequently, the user separately authorized the
[three-epoch comparison](0011-three-epoch-comparison.md), completed on 2026-10-11.
Its paired review preserves these original judgments and records both gains and
regressions rather than rewriting this review.

No training, inference, model/data download, GitHub metadata request, target
rewrite, test-split access, application integration, commit, or push occurred.
Only existing saved predictions and frozen validation diffs were evaluated.

## Selection and rubric

All data processing and artifact writes ran in native Windows `.venv-data`
under `D:\PushTrackML`; no packages or credentials were added.

- Freeze the first **20** SHA-256 ranks of `result-sample-42:` plus commit ID
  over the existing **962 validation rows**. No filtering by model outcome,
  replacement of difficult examples, or search for a more favorable seed.
- This extends experiment 0009's existing six-example prediction ordering.
  Those six output/reference pairs had already been seen; this review is
  explicitly **unblinded**, not a fresh blind evaluation.
- The selection covers **17 repositories**, with **two multi-file commits**.
  Multiple rows from some repositories remain correlated.
- Read every complete diff, original subject, and saved baseline/final output.
  Judge against the diff, **not agreement with the reference wording**.
- Record faithfulness, specificity, invented claims, English, coverage,
  reference limitations, evidence, and an overall decision separately.

Overall rubric, frozen in `sample.json` before reading all selected diffs:

| Decision | Meaning |
| --- | --- |
| Usable | Faithful, clear, and specific enough about the main visible change; exact wording and every minor detail are not required. |
| Needs edit | Grounded core, but too generic, incomplete, or awkward; no central unsupported/contradicted assertion. |
| Misleading | Central action/intent is unsupported or contradicted, or coverage misrepresents the change. |
| Unusable | Not an intelligible commit subject, e.g. denoising markers or repeated code fragments. |

Six judgments are marked interpretation-sensitive. In particular, the short
`Fixed duplicate key check` and `Update bundle version` subjects were accepted
without requiring every qualifier. Ambiguous shorthand about a missing URL,
CLI error handling, or ds-4 mappings was not automatically called hallucination.
The property-versus-property-usage distinction is also explicitly marked for
possible reviewer disagreement. Different reviewers may draw stricter or more
lenient acceptance boundaries.

## Results

| Overall decision | Pretrained baseline | After one epoch |
| --- | ---: | ---: |
| Usable | 0 | **3** |
| Needs edit | 0 | **12** |
| Misleading | 0 | **5** |
| Unusable/non-subject | **20** | 0 |

The baseline's lack of intelligible assertions was marked `not_assessable`, not
misrepresented as faithful text or a measured absence of hallucination.

Final-output dimensions (overlapping; do not add across dimensions):

- Faithfulness: **10 supported**, **5 partially supported**, **5 unsupported**.
- Specificity: **5 specific**, **10 generic**, **5 misleading**.
- Invented claims: **15 with none identified**, **2 contradicted claims**,
  **3 unsupported claims** under this rubric.
- English: **16 clear**, **4 awkward**. A Dutch holiday label inside an English
  subject is not itself a language error.
- Coverage: **10 sufficient**, **5 partial**, **5 misleading**.

Thus zero exact reference matches did not imply zero usable summaries. Equally,
short, fluent subjects and better validation loss did not establish faithfulness.

### Per-example record

Full diffs and annotations remain on Windows, outside Git. Commit prefixes below
identify the complete hashes in `sample.json` and `review.json`.

| # | Commit | Final subject | Decision and visible evidence |
| --- | --- | --- | --- |
| 1 | `77f914a4ba9b` | Add codeql path to readme | **Usable:** README adds a section documenting the `codeql-path` output. |
| 2 | `b2bfb13cf024` | Fixed duplicate key check | **Usable, borderline:** new operator-key uniqueness check rejects a key owned by another transaction. More scope would help, but the central check is described. |
| 3 | `96f6dc9fc50b` | Fix bug in uint256 | **Needs edit:** too generic about the `1` to `1U` shift-mask change. |
| 4 | `51c4eb5cc180` | Add mspythonconfig to workspaceContains | **Needs edit:** correctly captures an addition but misses narrowing the existing recursive pyright activation pattern. |
| 5 | `f6546b856775` | Add actionsheet props to actionsheet | **Needs edit:** repetitive and omits drag-indicator prop typings. |
| 6 | `0f5fe8b0c2e6` | Add development dependency to gemspec | **Misleading:** the dependency already exists; only its version constraint changes. |
| 7 | `a54772f7e45d` | Fix test for string containsString | **Needs edit:** awkward shorthand for replacing `assertContains` with `assertStringContainsString`. |
| 8 | `38a19b50a931` | Fix button icon alignment | **Misleading:** only the `iconAlign` documentation comment changes, not alignment behavior. |
| 9 | `3ff3c18eccef` | Added removed lost-cv image to CHANGELOG.md | **Needs edit:** awkward/ambiguous wording for a new image-removal changelog note. |
| 10 | `a532de42f0c0` | Fix missing URL for cnki.net | **Needs edit, borderline:** names the domain but misses its addition to a PDF blacklist. |
| 11 | `7cb7ad93731f` | Fix scssPHP compiler | **Needs edit:** omits adding configured paths to compiler import paths. |
| 12 | `85b01f778946` | Add error to cli | **Needs edit, borderline:** unclear about existing `CliError` gaining custom display and Click integration. |
| 13 | `99ffacac28cf` | Add ds-4 to browser | **Needs edit, borderline:** fails to identify the new infotip/tourtip mappings; the flag already exists elsewhere. |
| 14 | `8064007a3ef4` | Add langcode to useTranslation | **Misleading:** `langcode` is moved, not added; actual changes include namespace members and stricter parameter typing. |
| 15 | `e9712a16a473` | Fix Nager Date Test | **Needs edit:** misses framework retargeting from net45 to net472 in **both** test and library projects. |
| 16 | `fc385a7e095d` | Fix cpp grammar | **Misleading:** only `TODO` is added to an existing comment. |
| 17 | `f76d664e2dc5` | Fix group option | **Needs edit:** omits the guard change and changed treatment of empty group strings. |
| 18 | `76f16a197172` | fix: remove cacheable property | **Misleading, borderline:** removes testing-time use/override of a property, not its definition. |
| 19 | `235cc6a80d49` | Fix Goede Vrijdag | **Needs edit:** names the holiday but omits the local-name/translation correction. |
| 20 | `870e8e38d5aa` | Update bundle version | **Usable, borderline:** both files update the same bundle version; naming CodeQL/date would improve it but is not mandatory. |

The two multi-file outcomes (15 and 20) are insufficient to estimate general
multi-file competence. One missed the library/framework scope; the other
correctly covered two matching version edits.

## The references are not unquestioned ground truth

Reference-support judgments were **14 supported**, **2 partially supported**,
**3 needing external context**, and **1 unsupported**. These are annotations,
not new exclusions or rewritten labels:

- The Bundler reference claims compatibility with 2.0, while the diff only
  widens an existing 1.x development-dependency constraint. That compatibility
  claim is not demonstrated by this patch; the model's addition claim is also
  independently wrong about the visible modification.
- `wip`, a CodeQL release number not shown in the patch, and a private API being
  `no-longer-working` require context beyond the visible changes.
- The specific ProUpRegTx type is not named in its hunk context. An `Improve if
  clause` reference underdescribes the changed empty-string handling.

Do not force outputs to match weak references or call reference disagreement
alone a semantic error.

## Evidence and preservation

```text
D:\PushTrackML\runs\training-0002\quality-review-0001\
    sample.json
    review.json
    verification.json
    provenance\
        pushtrack-model-review-sample.py
        pushtrack-model-review-finalize.py
```

- Sample SHA-256:
  `b1201aa9f5e21c6c1d84b230b97d9bf1b3ba8ced7cd7705f1f0ddc2b548ff7bb`.
- Review SHA-256:
  `30f530e09300c44f7c08d16f584ed33a0ae4d0b0aec0d42784ba27f93f743b70`.
- Preservation/annotation verification SHA-256:
  `4e8f63a328e2922b31efb25e2a0b165857e884b9481914e94785328854f35bcf`.

Native assertions checked all 20 unique identities, complete sample coverage,
rubric values/category consistency, and unchanged hashes of **nine input
artifacts**: both data exports, their manifest, training report, step log,
checkpoint, baseline/final measurements, and previous reload verification.
This is an annotation/preservation check, not an independent semantic review or
a newly run application test suite. Dataset records and original targets were
not changed; optimizer updates and inference calls were both **zero**.

## Conclusion and proposed next experiment

The one-epoch model learned the requested output shape, but still often loses
specifics and sometimes invents the type of change. Use only with explicit
human review; do not enable unattended commit/push behavior.

A **separately approved three-epoch comparison from the original pretrained
weights**, using the same frozen data, is a reasonable bounded next experiment.
The single epoch, relatively close train/validation losses, and generic titles
make longer training worth testing; they do **not** prove undertraining rather
than weak labels is the cause, or that more epochs will fix semantic errors.
Preserve the current checkpoint, declare the new recipe before running it, and
compare loss **and** these failure modes. Do not simply optimize exact matches.

These inspected examples are now development evidence, not a blind final test.
Keep the test split untouched. No further training has been authorized or
started by this review; fork, label-quality, licensing, privacy, and deployment
limitations remain as documented in experiment 0009.

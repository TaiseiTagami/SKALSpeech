# Verifying anatomical EMA sensor-channel assignments

This procedure identifies which numbered channels in an original Rainbow EMA recording correspond to anatomical labels in the separately trimmed Rainbow TXT files. **Do not infer mappings solely from channel order or an existing SKALSpeech template.**

## Inputs and provenance

For each speaker, locate the original Rainbow recording under the source `pos` directory (tab-delimited TXT with `ChN_X`, `ChN_Y`, `ChN_Z` and other fields), and its Rainbow trimmed segments with a matching `*-header.txt` and numerical TXT. The SKALSpeech `tests/local/{als|control}/{speaker}/info.txt` may record the source path. Treat the original source directory as read-only. Also locate `corpus.yaml`, `column_templates/sensor_columns.yaml`, and the `recordings/silence/pos.txt` reference recording.

Check that the trim header and data have matching column counts and that sensor names such as PT, TT, LL, UL, JC, JM correspond to coordinate triplets. Inspect time/sample rates, units, missing-value conventions and precision; never assume the trim is byte-identical to raw data.

## 1. Recover the coordinate convention

For the examined Rainbow data, the observed correspondence was:

| Trim coordinate | Original Rainbow coordinate |
| --- | --- |
| `sensor x` | `ChN_Y` |
| `sensor y` | `ChN_Z` |
| `sensor z` | `ChN_X` |

This is an **empirical finding for these recordings**, not a universal rule. Recheck it against several sensors and segments for any new acquisition format. Account for possible sign flips, scaling, rounding and offsets if evidence requires them; document any transformation.

## 2. Identify the original sample offset and channel

For each trim sensor, take a contiguous window (e.g. 100 valid samples) of trim `sensor x`. For each candidate raw `ChN_Y`, slide that window along the original Rainbow time series and compute normalized Pearson correlation for every valid offset. A simple implementation may use `numpy.correlate` with sliding means and variances; exclude nonfinite and near-constant windows. Store **channel, correlation and raw start index**, not merely the highest correlation. Match the trim sequence against the same chronological raw sequence, not an unordered set of values.

Require several different anatomical sensors to identify their channels **at one shared raw sample offset**. A high correlation at a different offset is not sufficient: repeated gestures can produce convincing false matches. Check the best and second-best candidate, especially for slowly moving or stationary sensors.

The original investigation used `scripts/audit_trim_channel_correlations.py` as an exploratory single-axis audit. Its output distinguishes matches at the common offset from `other` matches at inconsistent offsets. It is **not** a final validator; its per-sensor unconstrained maximum can select a different segment of the recording.

## 3. Cross-validate with the other two axes

At the shared offset, compare trim `y` with raw `ChN_Z`, and trim `z` with raw `ChN_X`. Report correlation and an absolute error statistic (e.g. median absolute error after any documented rounding/coordinate transform), plus number of valid samples. Repeat using a second independent trim segment if available. Confirm a one-to-one mapping: no two anatomical labels may silently share a raw channel. Do not fill missing channels from a presumed conventional sequence.

As a concrete example, CMF28's first trim matched the original at **zero-based sample index 198**; PT=Ch7, TT=Ch16, LL=Ch9, UL=Ch10, JC=Ch14, JM=Ch15. The x/y/z permutation was essential to identifying these channels. Verify on the current files before reusing the result.

## 4. Decide and record confidence

Mark a mapping **verified** only when multiple sensors share the offset, all available axes agree, and there is no plausible competing channel. Mark **provisional** for limited or noisy evidence; mark **unresolved** when offsets disagree, files are missing, or channels collide. Save per-speaker evidence: raw and trim file identifiers, segment, window length, sample offset, axes, each candidate's correlation/error, accepted channel map, unresolved labels, and any manual review. Do not treat a high single-axis correlation alone as conclusive.

## 5. Back up and update SKALSpeech

Before edits, make a timestamped copy of each affected `corpus.yaml` **and** its `column_templates/sensor_columns.yaml`; also preserve any global template being changed. In this corpus layout, `columns: {}` in `corpus.yaml` means the effective sensor assignments can live in the speaker's `column_templates/sensor_columns.yaml`. Inspect both instead of editing only `corpus.yaml`.

Update the complete set of X/Y/Z/phi/theta/RMS labels for each verified channel, while retaining reference sensors (e.g. Ch4–Ch6) and the original raw channel names. Ensure each anatomical output label occurs once, and that all expected fields are present. Do not edit the original Vanderbilt source directories. For incomplete evidence, leave the uncertain mapping flagged rather than guessing.

Changing YAML **does not retroactively fix** existing `recordings/*/processed.csv` files. Reprocess affected Rainbow and silence recordings from their existing `pos.txt` with the corrected effective mapping; preserve annotations and unrelated data. Verify output headers and spot-check that each processed anatomical coordinate equals the corresponding raw channel coordinate at the same sample, subject to documented processing transformations.

## 6. Check resting-position plausibility

For each speaker's silence recording, obtain valid X/Z pairs for PT, TT, LL, UL, JC, JM using the **corrected** mapping. Exclude nonfinite coordinates and pairs where both coordinates are zero. Compute coordinate-wise medians and valid sample counts, preferably on a verified quiet interval. The MATLAB helper `ForcedAlignmentMatLab/Scripts/Analysis/CohortMidpointClouds/getRestBaselines.m` implements this median approach on processed silence CSVs.

Check for gross anatomical inconsistencies: tongue tip versus posterior tongue order, upper versus lower lip order in the dataset's established coordinate convention, implausibly large separations, near-identical supposedly independent sensors, extreme values, and unexpectedly identical recordings across speakers. Inspect trajectories and recording quality before concluding that an odd geometry proves a channel swap. Compare against each speaker's own geometry and data units; no universal numerical threshold is guaranteed.

Record missing baselines separately from bad mappings. For example, CMF32's proposed JM=Ch13 yielded no valid X/Z rest pairs under this rule, so its JM baseline is unavailable; this alone does **not** disprove the channel identity. Previously observed CMF16/CMF18/CMF21 identical resting data reflected a separate duplicate-data problem, not three independent confirmations.

## 7. Final validation checklist

- Original raw data untouched; mapping files backed up.
- Anatomical channel identities supported by shared-offset, multi-axis trim matches.
- One-to-one assignment and effective YAML mapping verified.
- Unresolved labels/corpora explicitly documented.
- Affected processed Rainbow and silence CSVs regenerated and checked against raw columns.
- Rest medians, valid counts, sensor geometry and recording-level anomalies reviewed.
- MATLAB analyses rerun only after regenerated data have been verified.

Never describe an unregenerated CSV as corrected merely because its mapping YAML was updated.

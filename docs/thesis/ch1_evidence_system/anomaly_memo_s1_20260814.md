# S1 live-smoke anomaly memo — 2026-08-14

The first authorized S1 attempt at commit `2d0a106` reached SiliconFlow and
returned a valid Manager decision, but ended as `needs_clarification` before
any tool call. The Manager asked the user to supply imagery even though the
runtime already held one local raster. The external evaluator therefore failed
and the batch stopped; S2 and S3 were not run.

This was a model-context contract defect: path redaction removed all evidence
that input data existed. The remediation adds only two non-sensitive facts to
the model view, `input_data_available` and `input_data_count`, and tells the
Manager not to request a path/upload when that flag is true. Paths, filenames,
raster data and hidden evaluator facts remain excluded.

The failed run is retained under
`ExpertsRS/results/ch1_d3_light/authorized_smoke/`; it must not be overwritten
or silently counted as a passing smoke. A rerun must use a new destination and
a new committed code identity.

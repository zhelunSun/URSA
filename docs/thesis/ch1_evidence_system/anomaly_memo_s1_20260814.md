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

The first remediation rerun at commit `15b5c66` also stopped at Manager
clarification. It correctly recognized that an input existed, but asked the
user for sensor/band and clipping details that the Scientist and metadata tool
are responsible for discovering. That run is retained under
`authorized_smoke_rerun_15b5c66/`. The second remediation narrows the Manager
contract: clarification is limited to ambiguous analysis goals, metrics, or
outputs; technical raster preconditions must be delegated to Scientist/tools.

At commit `47a0d3f`, S1 passed Manager routing and completed metadata, NDVI and
map production, but the final report referenced only the map instead of the
complete validated artifact manifest. Runtime correctly returned
`report_failed`; the run is retained under `authorized_smoke_rerun_47a0d3f/`.
The report prompt is therefore aligned with the already-enforced WP3 contract:
reference every supplied validated artifact ID exactly once and invent none.

At commit `649e25a`, S1 again produced all three artifacts, then Engineer
returned an incomplete `{"kind":"stop"}` object. The strict action parser
correctly rejected it because `reason` is required. The Engineer prompt had
named stop/revise as options without spelling out their schemas. The prompt is
corrected to give the exact stop and revise objects and to require a Manager
handoff after requested outputs have been produced.

At commit `72fb889`, S1 passed. S2 created and reused the NDVI checkpoint, but
the model retried the seeded threshold failure without first emitting a
`revise` decision. The retry succeeded, then the original 18,000-token ceiling
stopped the run at 21,754 recorded tokens. Runtime now requires an explicit
revision in `revision_required` phase before any retry, and the test-stage
ceiling is raised to 45,000 tokens (still at most CNY 0.09/run at the reviewed
V4-Flash output rate).

At commit `4cd1582`, S1 passed and S2 produced plan v2, reused its checkpoint,
retried threshold successfully and preserved a single NDVI calculation. It
then stopped before `calculate_area` because the Engineer tool-call cap was 6:
the normal greenspace chain consumes six calls and the injected failure adds a
seventh. The reviewed cap is corrected to 8 Engineer calls within the existing
10-call global limit. Observed cumulative reasoning usage also motivates a
70,000-token ceiling; the reviewed price ceiling remains only CNY 0.14/run.

At commit `71d9d35`, S1 passed and S2 remained within the revised token/tool
limits, but the 300-second run wall-time expired after the recovered thematic
map and before area/report completion. The per-provider-call timeout remains
120 seconds; only the encompassing serial run wall-time is raised to 600
seconds, without changing retry, token, turn or tool limits.

At the final frozen attempt on commit `175a248`, S1 passed again. During S2,
SiliconFlow exceeded the 120-second single-call timeout after metadata and the
checkpointed NDVI artifact. Zero-retry policy preserved the provider failure
and stopped the batch; S3 was not run. This is retained as provider-stability
evidence, not silently replaced. The local API gate was closed after the run.

Current L1 decision: **NO-GO** for the 15-case pilot. A later reviewed smoke
window may rerun all three fixed slots in a new directory, but must retain and
report these failed attempts.

The first Paratera smoke attempt at commit `f5cfe77` reached the model but
failed before action because V4-Flash exhausted the 1,024 completion limit in
hidden reasoning and returned no final JSON. A controlled 8,192-token probe
ended normally with valid JSON (reasoning was not stored or displayed). The
per-call completion ceiling is therefore raised to 8,192 while the outer
70,000-token, 12-turn, 10-tool and zero-retry limits remain in force.

At Paratera commit `4cf2d38`, S1 passed and S2 correctly produced the full
recovery chain through area statistics. Engineer then proposed a duplicate
threshold action with an unapproved parameter instead of handing off for the
report; runtime rejected it without executing the unsafe action. The Engineer
contract now explicitly forbids repeating successful tools and requires a
Manager handoff when the requested artifacts are present.

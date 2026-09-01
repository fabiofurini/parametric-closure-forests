# Reproducibility

## Build and test

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
```

Debug builds with sanitizers (used in `.github/workflows/ci.yml`):

```bash
cmake -S . -B build-asan -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer"
cmake --build build-asan -j
ctest --test-dir build-asan --output-on-failure
```

## Regenerating instances

No bulk instance archive is stored in git (see `.gitignore`); every archive
used in a campaign is reproducible byte-for-byte from a generator plus its
recorded seed:

```bash
python3 tools/generate_random_instances.py --output instances/<name> \
  --sizes 100,200,500,1000 --densities 0.3,0.6,0.9,1.0 --topology gen --seeds 10
python3 tools/generate_structured_instances.py --output instances/<name> \
  --shape path --sizes 100,200,500,1000,2000 --seeds 10

python3 tools/build_instance_manifest.py --instances instances/<name> \
  --output instances/manifests/<name>.json
python3 tools/build_instance_manifest.py --instances instances/<name> \
  --verify instances/manifests/<name>.json
```

`build_instance_manifest.py --verify` fails loudly (non-zero exit) if a
single regenerated `.pcf` file's SHA-256, node/arc count, topology
classification or coefficient bounds differ from what is committed in
`instances/manifests/`. This is the standard way to confirm a regenerated
archive equals the one used for a published result.

## Running a campaign and rebuilding its tables

```bash
python3 tools/run_benchmark.py --binary build/pcf_benchmark \
  --instances instances/<name> --output results/raw_<campaign>.csv \
  --algorithms hpac,rac --repetitions 11 --shuffle-seed 1 --campaign-id <campaign>

python3 tools/validate_raw_data.py --raw results/raw_<campaign>.csv \
  --instances-root instances/<name>

python3 tools/aggregate_results.py --raw results/raw_<campaign>.csv \
  --output-dir results/processed/<campaign>

python3 tools/emit_latex_tables.py --mode ratio \
  --processed-dir results/processed/<campaign> --output results/tables/<campaign>_ratio.tex \
  --campaign-id <campaign> --baseline hpac --candidate rac --group-by n_nodes
```

No number in a committed `.tex` table fragment is hand-typed: regenerating a
table from the same raw CSV must reproduce it exactly (byte-for-byte, since
`tools/emit_latex_tables.py` has no non-deterministic step).

`tools/build_report.sh` runs the full pipeline above for every official
campaign at once. Its raw CSVs (`results/raw/*.csv`) are committed to git,
but the `.pcf` instance files they reference are not (see "Large instance
archives" below); `validate_raw_data.py` needs those files to confirm every
referenced instance actually exists, so on a fresh clone `build_report.sh`
fails at the validation step until the release instance archives (or a regenerated
equivalent) has been downloaded and extracted into `instances/`. The
already-committed `results/processed/` and `results/tables/*.tex` are the
exact output of the last time this pipeline was run against the full
archive and are available immediately, without any download, for anyone who
only wants the numbers rather than to regenerate them from scratch.

## Large instance archives and raw data

Full-scale campaign archives (campaigns C and E reach `n=100000`) and their
raw CSV output are attached as compressed assets on the GitHub release that
accompanies the manuscript's computational section, rather than committed
to git history; the instance archive is split under GitHub's 2 GiB asset
cap (`instances_b_d_fixtures.zip`, `instances_c.zip`, `instances_e_in.zip`,
`instances_e_out.zip`). The manifest
SHA-256 checksums under `instances/manifests/` let anyone verify a
downloaded or regenerated archive against the one actually used, without
needing git history to carry the binary data.

## Clean-clone independence test

Before any publication, this checklist must pass starting from a fresh clone
in an otherwise empty directory, with `PAPER/`, `CODE_FOREST/`,
`CODE_PARAMETRIC_PSEUDOFLOW/` and `GITHUB/` (the legacy workspace) not even
present on the machine:

1. `git clone <repo-url> clean && cd clean`
2. download instance/result assets referenced by the release notes, if any
   are needed for the check being run
3. verify their SHA-256 against `instances/manifests/*.json`
4. `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j`
   with no reference to any path outside the clone
5. `ctest --test-dir build --output-on-failure`
6. `python3 tools/generate_random_instances.py --output /tmp/smoke --sizes 50 --seeds 1`
7. run `python3 tools/build_instance_manifest.py --instances instances/tiny --verify instances/manifests/tiny.json`
   (or the committed fixture manifest) against a tracked small fixture
8. `build/pcf_solve --instance instances/mixed_tree.pcf --algorithm pac`,
   `...--algorithm hpac`, `...--algorithm rac` and diff the outputs
9. `python3 tools/run_bppf_native_campaign.py ...` on one small instance
   (BPPF comparison driver smoke test)
10. `tools/run_benchmark.py` on the `/tmp/smoke` instances followed by
    `tools/aggregate_results.py` and `tools/emit_latex_tables.py`, producing
    a table from data generated entirely inside the clean clone

The gate passes only if every step above succeeds without touching
`CODE_FOREST`, `GITHUB`, `PAPER` or any other file from the parent
workspace. This checklist is exercised by hand before each release; it is
not (yet) wired into `.github/workflows/ci.yml` as a separate job, since CI
already runs from a fresh checkout on every push and therefore already
satisfies steps 1 and 4-5 on every commit.

## Release contents

A GitHub release accompanying the manuscript packages:

- the source tree at the exact tag/commit used for the campaign;
- the split instance archive (`instances_b_d_fixtures.zip`,
  `instances_c.zip`, `instances_e_in.zip`, `instances_e_out.zip`) covering
  every campaign cited in the manuscript, plus `instances/manifests/*.json`;
- `results/raw_*.csv` (raw, uncorrected) and `results/processed/*` (derived);
- `results/results_summary.json`;
- the environment description from `docs/EXPERIMENTAL_PROTOCOL.md`;
- SHA-256 checksums for every attached asset.

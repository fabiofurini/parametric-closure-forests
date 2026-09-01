#!/usr/bin/env bash
# Packages the full instance archive and raw/processed results as release
# assets (plan section 4 and 14.2): large data is attached to a GitHub
# release, not committed to git history. Run after
# tools/run_night_sweep.sh and tools/build_report.sh have produced their
# output.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p dist
# GitHub caps release assets at 2 GiB each, so the instance archive is
# split: one zip for the medium/structured campaigns plus manifests and
# fixtures, and one zip per large campaign (C, E-in, E-out).
echo "=== zipping instances (split archives, 2 GiB asset cap) ==="
rm -f dist/instances*.zip dist/instances*.sha256
zip -rq -X dist/instances_b_d_fixtures.zip \
  instances/campaign_b \
  instances/campaign_d_path instances/campaign_d_binary instances/campaign_d_star \
  instances/manifests instances/tiny instances/mixed_tree.pcf
zip -rq -X dist/instances_c.zip instances/campaign_c
zip -rq -X dist/instances_e_in.zip instances/campaign_e_in
zip -rq -X dist/instances_e_out.zip instances/campaign_e_out
for z in dist/instances_*.zip; do
  sha256sum "$z" > "$z.sha256"
  echo "$z: $(du -h "$z" | cut -f1)"
done

echo "=== zipping raw + processed results ==="
zip -rq -X dist/results.zip results/raw results/processed results/tables results/logs
sha256sum dist/results.zip > dist/results.zip.sha256
echo "results.zip: $(du -h dist/results.zip | cut -f1)"

echo "=== dist/ contents ==="
ls -la dist/

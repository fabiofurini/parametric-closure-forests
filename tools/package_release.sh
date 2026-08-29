#!/usr/bin/env bash
# Packages the full instance archive and raw/processed results as release
# assets (plan section 4 and 14.2): large data is attached to a GitHub
# release, not committed to git history. Run after
# tools/run_official_campaigns.sh, tools/run_bppf_campaign.py and
# tools/build_report.sh have all produced their output.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p dist
echo "=== zipping instances (campaign_* directories + manifests) ==="
zip -rq -X dist/instances.zip \
  instances/campaign_b instances/campaign_c \
  instances/campaign_d_path instances/campaign_d_binary instances/campaign_d_star \
  instances/campaign_e_in instances/campaign_e_out instances/campaign_f \
  instances/manifests instances/tiny instances/mixed_tree.pcf \
  -x '*.failures.csv' -x '*_pac_subset/*' -x '*_large_only/*'
sha256sum dist/instances.zip > dist/instances.zip.sha256
echo "instances.zip: $(du -h dist/instances.zip | cut -f1)"

echo "=== zipping raw + processed results ==="
zip -rq -X dist/results.zip results/raw results/processed results/tables results/logs
sha256sum dist/results.zip > dist/results.zip.sha256
echo "results.zip: $(du -h dist/results.zip | cut -f1)"

echo "=== dist/ contents ==="
ls -la dist/

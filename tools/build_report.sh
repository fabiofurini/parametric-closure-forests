#!/usr/bin/env bash
# One-shot analysis pipeline (plan section 13): raw CSVs -> validated ->
# aggregated -> LaTeX table fragments + results_summary.json. Run after
# tools/run_official_campaigns.sh (and tools/run_bppf_campaign.py for
# campaign F) have produced results/raw/*.csv.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p results/processed results/tables

echo "=== validating raw CSVs ==="
python3 tools/validate_raw_data.py --raw results/raw/*.csv --instances-root .

echo "=== aggregating ==="
python3 tools/aggregate_results.py --raw results/raw/*.csv --output-dir results/processed

echo "=== emitting tables ==="
python3 tools/emit_latex_tables.py --mode correctness --processed-dir results/processed \
  --output results/tables/correctness.tex

emit_ratio() {
  local campaign=$1 baseline=$2 candidate=$3 group=$4
  python3 tools/emit_latex_tables.py --mode ratio --processed-dir results/processed \
    --output "results/tables/${campaign}_${candidate}_over_${baseline}_by_${group}.tex" \
    --campaign-id "${campaign}" --baseline "${baseline}" --candidate "${candidate}" --group-by "${group}" \
    || echo "  (skipped: no paired rows for ${campaign} ${candidate}/${baseline})"
}

emit_ratio campaign_b hfma rac n_nodes
emit_ratio campaign_b fma hfma n_nodes
emit_ratio campaign_c hfma rac n_nodes
emit_ratio campaign_d_path hfma rac n_nodes
emit_ratio campaign_d_binary hfma rac n_nodes
emit_ratio campaign_d_star hfma rac n_nodes
emit_ratio campaign_d_star fma hfma n_nodes
emit_ratio campaign_e_in hfma hima n_nodes
emit_ratio campaign_e_in hfma rac n_nodes
emit_ratio campaign_e_out hfma homa n_nodes
emit_ratio campaign_e_out hfma rac n_nodes

echo "=== done: results/processed/results_summary.json, results/tables/*.tex ==="
cat results/processed/results_summary.json

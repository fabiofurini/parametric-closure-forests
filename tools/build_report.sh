#!/usr/bin/env bash
# One-shot analysis pipeline (plan section 13): raw CSVs -> validated ->
# aggregated -> LaTeX table fragments + results_summary.json. Run after
# tools/run_official_campaigns.sh, tools/run_dual_variant_campaigns.sh and
# tools/run_bppf_campaign.py have produced results/raw/*.csv. Reproduces
# every number and table cited in
# Parametric_Closure/PAPER_MARCO/computational_section_v2.tex from raw data.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p results/processed results/tables

# campaign_f_bppf.csv (tools/run_bppf_campaign.py) and *.failures.csv use a
# different schema than pcf_benchmark's CSV and are handled separately below.
mapfile -t STANDARD_RAW < <(ls results/raw/campaign_{b,c,d_path,d_binary,d_star,e_in,e_out}_*.csv 2>/dev/null \
  | grep -v '\.failures\.csv$')

echo "=== validating standard-schema raw CSVs ==="
for csv in "${STANDARD_RAW[@]}"; do
  # Each row's "instance" column is a bare filename; resolve it against the
  # campaign's own instance directory (recorded in the campaign_id column),
  # since the same basename can be symlinked into more than one directory
  # (e.g. the PaC-eligible size subsets).
  campaign_id=$(awk -F, 'NR==2{print $1}' "$csv")
  python3 tools/validate_raw_data.py --raw "$csv" --instances-root "instances/${campaign_id}"
done

echo "=== aggregating ==="
python3 tools/aggregate_results.py --raw "${STANDARD_RAW[@]}" --output-dir results/processed

echo "=== emitting tables ==="
python3 tools/emit_latex_tables.py --mode correctness --processed-dir results/processed \
  --output results/tables/correctness.tex

emit_ratio() {
  local campaign=$1 baseline=$2 candidate=$3 group=${4:-n_nodes}
  python3 tools/emit_latex_tables.py --mode ratio --processed-dir results/processed \
    --output "results/tables/${campaign}_${candidate}_over_${baseline}.tex" \
    --campaign-id "${campaign}" --baseline "${baseline}" --candidate "${candidate}" --group-by "${group}" \
    || echo "  (skipped: no paired rows for ${campaign} ${candidate}/${baseline})"
}

emit_ratio campaign_b hpac rac
emit_ratio campaign_b hpac pac
emit_ratio campaign_b hpac dhpac
emit_ratio campaign_c hpac rac
emit_ratio campaign_c hpac dhpac
emit_ratio campaign_d_path hpac rac
emit_ratio campaign_d_binary hpac rac
emit_ratio campaign_d_star hpac rac
emit_ratio campaign_d_star hpac dhpac
emit_ratio campaign_d_star pac hpac
emit_ratio campaign_e_in hpac hipac
emit_ratio campaign_e_in hpac rac
emit_ratio campaign_e_out hpac hopac
emit_ratio campaign_e_out hpac rac

echo "=== campaign F (BPPF baseline) summary ==="
python3 - <<'EOF'
import csv
rows = list(csv.DictReader(open("results/raw/campaign_f_bppf.csv")))
mismatches = sum(int(r["bppf_mismatches"]) for r in rows)
ratios = sorted(float(r["bppf_median_total_ns"]) / float(r["hpac_median_ns"]) for r in rows)
print(f"instances={len(rows)} mismatches={mismatches} "
      f"bppf_total/hpac ratio range=[{ratios[0]:.1f}, {ratios[-1]:.1f}]")
EOF

echo "=== done: results/processed/results_summary.json, results/tables/*.tex ==="
cat results/processed/results_summary.json

#!/usr/bin/env bash
# One-shot analysis pipeline: raw CSVs -> validated -> aggregated -> LaTeX
# table fragments + results_summary.json. Run after
# tools/run_official_campaigns.sh, tools/run_dual_variant_campaigns.sh and
# tools/run_bppf_native_campaign.py have produced results/raw/*.csv.
# Reproduces every number and table cited in the manuscript from raw data.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p results/processed results/tables

# campaign_g_bppf_native.csv (tools/run_bppf_native_campaign.py) and
# *.failures.csv use a different schema than pcf_benchmark's CSV and are
# handled separately below.
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
# Per-density view of the same campaign-C pairing (plan V3 decision #6:
# the rho=1.0 crossover check). The output name needs the _by_rho suffix,
# so this one is spelled out rather than routed through emit_ratio.
python3 tools/emit_latex_tables.py --mode ratio --processed-dir results/processed \
  --output results/tables/campaign_c_rac_over_hpac_by_rho.tex \
  --campaign-id campaign_c --baseline hpac --candidate rac --group-by rho \
  || echo "  (skipped: no paired rows for campaign_c rac/hpac by rho)"
emit_ratio campaign_d_path hpac rac
emit_ratio campaign_d_binary hpac rac
emit_ratio campaign_d_star hpac rac
emit_ratio campaign_d_star hpac dhpac
emit_ratio campaign_d_star pac hpac
emit_ratio campaign_d_star pac rac
emit_ratio campaign_e_in hpac hipac
emit_ratio campaign_e_in hpac rac
emit_ratio campaign_e_out hpac hopac
emit_ratio campaign_e_out hpac rac

echo "=== emitting the detailed report fragments (report/) ==="
python3 tools/emit_report_tables.py
# per-algorithm workload table (from the aggregate summary)
python3 - <<'PYSNIP'
import json, csv, pathlib
from collections import defaultdict
s = json.load(open("results/processed/results_summary.json"))
NICE = {"pac":"PaC","dpac":"DPaC","hpac":"HPaC","dhpac":"DHPaC",
        "hipac":"HIPaC","hopac":"HOPaC","rac":"RaC"}
inst = defaultdict(set)
for r in csv.DictReader(open("results/processed/processed.csv")):
    inst[r["algorithm"]].add((r["campaign_id"], r["instance"]))
lines = ["\\begin{tabular}{@{}lrrr@{}}", "\\toprule",
         "algorithm & instances & timed runs & runs/instance \\\\", "\\midrule"]
for a in ["pac","dpac","hpac","dhpac","hipac","hopac","rac"]:
    n_i, n_r = len(inst[a]), s["runs_per_algorithm"][a]
    lines.append(f"\\texttt{{{NICE[a]}}} & {n_i:,} & {n_r:,} & {n_r/n_i:.1f} \\\\".replace(",", "\\,"))
lines += ["\\midrule",
          f"total & {s['n_instances']:,} & {s['n_raw_rows']:,} & \\\\".replace(",", "\\,"),
          "\\bottomrule", "\\end{tabular}"]
pathlib.Path("results/tables/rep_runs_per_algorithm.tex").write_text("\n".join(lines)+"\n")
print("wrote results/tables/rep_runs_per_algorithm.tex")
PYSNIP

# layer-size statistics (runs pcf_solve on a sample; skipped if solver missing)
if [ -x build/pcf_solve ]; then
  python3 tools/layer_size_stats.py --pcf-solve build/pcf_solve \
    --instances instances/campaign_c      --pattern 'gen_n10000_*_seed0.pcf' \
    --instances instances/campaign_d_star --pattern 'star_n10000_*_seed0.pcf' \
    --instances instances/campaign_d_path --pattern 'path_n10000_*_seed0.pcf' \
    --instances instances/campaign_e_in   --pattern 'in_n10000_*_seed0.pcf' \
    --output-dir results/tables
fi

echo "=== campaign G (BPPF native comparison) summary ==="
if [ -f results/raw/campaign_g_bppf_native.csv ]; then
python3 - <<'EOF'
import csv, statistics
rows = list(csv.DictReader(open("results/raw/campaign_g_bppf_native.csv")))
bad = [r for r in rows if r["agrees_or_tolerance_explained"] != "True"]
ratios = sorted(float(r["bppf_internal_median_ns"]) / float(r["hpac_median_ns"]) for r in rows)
print(f"instances={len(rows)} genuine_disagreements={len(bad)} "
      f"bppf_internal/hpac median={statistics.median(ratios):.1f} range=[{ratios[0]:.1f}, {ratios[-1]:.1f}]")
EOF
else
  echo "campaign_g_bppf_native.csv not present, skipping"
fi

echo "=== done: results/processed/results_summary.json, results/tables/*.tex ==="
cat results/processed/results_summary.json

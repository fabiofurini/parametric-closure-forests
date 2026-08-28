#!/usr/bin/env bash
# Official benchmark campaigns (docs/PIANO_PARTE_COMPUTAZIONALE.md section 9,
# scoped per docs/EXPERIMENTAL_PROTOCOL.md). Generates every instance archive
# deterministically, runs each algorithm in its own subprocess with a
# wall-clock timeout and a memory ceiling (tools/run_benchmark.py), and
# leaves raw CSVs under results/raw/ for tools/aggregate_results.py.
#
# FMA is included only up to a preregistered size cutoff (n<=20000 for
# random/campaign C, n<=2000 for structured/campaign D) with fewer
# repetitions, since it is a reference baseline, not a headline comparison,
# and its own O(n^2)-ish scaling makes the full large-n matrix impractical
# (see the timing calibration referenced in EXPERIMENTAL_PROTOCOL.md).
#
# Usage: tools/run_official_campaigns.sh [campaign ...]
#   with no arguments, runs b c d e in sequence.
set -euo pipefail
cd "$(dirname "$0")/.."

BIN=build/pcf_benchmark
GEN_RANDOM="python3 tools/generate_random_instances.py"
GEN_STRUCT="python3 tools/generate_structured_instances.py"
RUN="python3 tools/run_benchmark.py"
MEM_LIMIT_KIB=8000000     # 8 GiB safety ceiling; see docs/EXPERIMENTAL_PROTOCOL.md
TIMEOUT_S=300
CORE=0
TASKSET=""
if command -v taskset >/dev/null 2>&1; then TASKSET="taskset -c ${CORE}"; fi

run() {
  # run <instances-dir> <algorithms> <repetitions> <campaign-id> <shuffle-seed>
  local dir=$1 algs=$2 reps=$3 cid=$4 seed=$5
  local out=results/raw/${cid}_${algs//,/-}.csv
  echo "=== ${cid} :: ${algs} (${reps} reps) on ${dir} -> ${out} ==="
  ${TASKSET} ${RUN} --binary "${BIN}" --instances "${dir}" --output "${out}" \
    --algorithms "${algs}" --repetitions "${reps}" --campaign-id "${cid}" \
    --shuffle-seed "${seed}" --timeout-seconds "${TIMEOUT_S}" --memory-limit-kib "${MEM_LIMIT_KIB}"
}

campaign_b() {
  local dir=instances/campaign_b
  [ -d "${dir}" ] || ${GEN_RANDOM} --output "${dir}" \
    --sizes 100,200,300,400,500,600,700,800,900,1000 \
    --densities 0.3,0.6,0.9,1.0 --topology gen --seeds 10
  run "${dir}" fma,hfma,rac 11 campaign_b 1
}

campaign_c() {
  local dir=instances/campaign_c
  [ -d "${dir}" ] || ${GEN_RANDOM} --output "${dir}" \
    --sizes 10000,20000,30000,40000,50000,60000,70000,80000,90000,100000 \
    --densities 0.3,0.6,0.9,1.0 --topology gen --seeds 10
  run "${dir}" hfma,rac 3 campaign_c 2

  local fma_subset=instances/campaign_c_fma_subset
  if [ ! -d "${fma_subset}" ]; then
    mkdir -p "${fma_subset}"
    find "${dir}" -name 'gen_n10000_*' -exec ln -sf "$(pwd)/{}" "${fma_subset}/" \;
  fi
  run "${fma_subset}" fma 2 campaign_c 2
}

campaign_d() {
  for shape in path binary star; do
    local dir=instances/campaign_d_${shape}
    [ -d "${dir}" ] || ${GEN_STRUCT} --output "${dir}" --shape "${shape}" \
      --sizes 100,200,500,1000,2000,5000,10000,20000,50000,100000 --seeds 10
    run "${dir}" hfma,rac 3 campaign_d_${shape} 3

    local fma_subset=instances/campaign_d_${shape}_fma_subset
    if [ ! -d "${fma_subset}" ]; then
      mkdir -p "${fma_subset}"
      for n in 100 200 500 1000 2000; do
        find "${dir}" -name "${shape}_n${n}_*" -exec ln -sf "$(pwd)/{}" "${fma_subset}/" \;
      done
    fi
    run "${fma_subset}" fma 3 campaign_d_${shape} 3
  done
}

campaign_e() {
  for topo in in out; do
    local dir=instances/campaign_e_${topo}
    [ -d "${dir}" ] || ${GEN_RANDOM} --output "${dir}" \
      --sizes 100,200,300,400,500,600,700,800,900,1000,10000,20000,30000,40000,50000,60000,70000,80000,90000,100000 \
      --densities 0.6,1.0 --topology "${topo}" --seeds 5
    local specialized=hima
    [ "${topo}" = out ] && specialized=homa
    run "${dir}" "hfma,${specialized},rac" 3 "campaign_e_${topo}" 4
  done
}

mkdir -p results/raw
targets=("$@")
[ ${#targets[@]} -eq 0 ] && targets=(b c d e)
for target in "${targets[@]}"; do
  "campaign_${target}"
done
echo "=== official campaigns finished: $(date -u +%FT%TZ) ==="

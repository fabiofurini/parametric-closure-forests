#!/usr/bin/env bash
# Official benchmark campaigns (docs/PIANO_PARTE_COMPUTAZIONALE.md section 9,
# scoped per docs/EXPERIMENTAL_PROTOCOL.md). Generates every instance archive
# deterministically, runs each algorithm in its own subprocess with a
# wall-clock timeout and a memory ceiling (tools/run_benchmark.py), and
# leaves raw CSVs under results/raw/ for tools/aggregate_results.py.
#
# PaC is included only up to a preregistered size cutoff (n<=20000 for
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
  # run <instances-dir> <algorithms> <repetitions> <campaign-id> <shuffle-seed> [output-tag]
  # output-tag distinguishes several passes that share a campaign id and an
  # algorithm list but run on different instance subsets (e.g. PaC at
  # n=10000 and at n=20000 within campaign C).
  local dir=$1 algs=$2 reps=$3 cid=$4 seed=$5 tag=${6:-}
  local out=results/raw/${cid}${tag:+_${tag}}_${algs//,/-}.csv
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
  run "${dir}" pac,hpac,rac 11 campaign_b 1
}

campaign_c() {
  local dir=instances/campaign_c
  [ -d "${dir}" ] || ${GEN_RANDOM} --output "${dir}" \
    --sizes 10000,20000,30000,40000,50000,60000,70000,80000,90000,100000 \
    --densities 0.3,0.6,0.9,1.0 --topology gen --seeds 10
  run "${dir}" hpac,rac 3 campaign_c 2

  # PaC is affordable only at the two smallest sizes of this test bed; it is
  # run there as a reference baseline (see the size cutoff note at the top of
  # this file). DPaC is run on the same two subsets by
  # tools/run_dual_variant_campaigns.sh, which reuses these directories.
  local n10k_subset=instances/campaign_c_n10000_subset
  if [ ! -d "${n10k_subset}" ]; then
    mkdir -p "${n10k_subset}"
    find "${dir}" -name 'gen_n10000_*' -exec ln -sf "$(pwd)/{}" "${n10k_subset}/" \;
  fi
  run "${n10k_subset}" pac 2 campaign_c 2 n10000

  local n20k_subset=instances/campaign_c_n20000_subset
  if [ ! -d "${n20k_subset}" ]; then
    mkdir -p "${n20k_subset}"
    find "${dir}" -name 'gen_n20000_*' -exec ln -sf "$(pwd)/{}" "${n20k_subset}/" \;
  fi
  run "${n20k_subset}" pac 3 campaign_c 2 n20000
}

campaign_d() {
  for shape in path binary star; do
    local dir=instances/campaign_d_${shape}
    [ -d "${dir}" ] || ${GEN_STRUCT} --output "${dir}" --shape "${shape}" \
      --sizes 100,200,500,1000,2000,5000,10000,20000,50000,100000 --seeds 10
    run "${dir}" hpac,rac 3 campaign_d_${shape} 3

    if [ "${shape}" = star ]; then
      # Run both O(n)-space heap variants on the complete star matrix. They
      # use the same instances, repetitions, shuffle seed, timeout and memory
      # ceiling as the HPaC/RaC comparison above.
      run "${dir}" hpac_eager 3 campaign_d_star 3
      run "${dir}" hpac_bounded 3 campaign_d_star 3

      # HPaC is known to exhaust the memory ceiling on large mixed-star
      # instances (docs/EXPERIMENTAL_PROTOCOL.md). Since hpac and rac run in
      # the same process above, an HPaC memory failure also loses RaC's
      # result for that instance even though RaC alone is unaffected. Recover
      # it with a RaC-only pass restricted to the sizes where this happens.
      local large_only=instances/campaign_d_star_large_only
      if [ ! -d "${large_only}" ]; then
        mkdir -p "${large_only}"
        for n in 20000 50000 100000; do
          find "${dir}" -name "star_n${n}_*" -exec ln -sf "$(pwd)/{}" "${large_only}/" \;
        done
      fi
      run "${large_only}" rac 3 campaign_d_star 3
    fi

    local pac_subset=instances/campaign_d_${shape}_pac_subset
    if [ ! -d "${pac_subset}" ]; then
      mkdir -p "${pac_subset}"
      for n in 100 200 500 1000 2000; do
        find "${dir}" -name "${shape}_n${n}_*" -exec ln -sf "$(pwd)/{}" "${pac_subset}/" \;
      done
    fi
    run "${pac_subset}" pac 3 campaign_d_${shape} 3
  done
}

campaign_e() {
  for topo in in out; do
    local dir=instances/campaign_e_${topo}
    [ -d "${dir}" ] || ${GEN_RANDOM} --output "${dir}" \
      --sizes 100,200,300,400,500,600,700,800,900,1000,10000,20000,30000,40000,50000,60000,70000,80000,90000,100000 \
      --densities 0.3,0.6,0.9,1.0 --topology "${topo}" --seeds 10
    local count
    count=$(find "${dir}" -maxdepth 1 -type f -name '*.pcf' -printf . | wc -c)
    if [ "${count}" -ne 4800 ]; then
      echo "campaign E ${topo}: expected 4,800 instances in ${dir}, found ${count}; refusing a partial run" >&2
      return 1
    fi
    local specialized=hipac
    [ "${topo}" = out ] && specialized=hopac
    run "${dir}" "hpac,${specialized},rac" 3 "campaign_e_${topo}" 4
  done
}

mkdir -p results/raw
targets=("$@")
[ ${#targets[@]} -eq 0 ] && targets=(b c d e)
for target in "${targets[@]}"; do
  "campaign_${target}"
done
echo "=== official campaigns finished: $(date -u +%FT%TZ) ==="

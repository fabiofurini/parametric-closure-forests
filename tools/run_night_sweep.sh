#!/usr/bin/env bash
# One-command overnight sweep for the V3 redo (docs/EXPERIMENTAL_PLAN_V3.md,
# §4bis). Phase 1 (instances + manifest verification) runs first, serially;
# then the campaign lanes run in parallel, each pinned to its own physical
# P-core via the PCF_CORE override of the two campaign scripts. Every lane
# logs to results/logs/night_<lane>_<stamp>.log; the script waits for all
# lanes and prints a completion summary.
set -euo pipefail
cd "$(dirname "$0")/.."

STAMP=$(date -u +%Y%m%d_%H%M)
LOGDIR=results/logs
mkdir -p "${LOGDIR}" results/raw results/processed results/tables

GEN_RANDOM="python3 tools/generate_random_instances.py"
GEN_STRUCT="python3 tools/generate_structured_instances.py"

echo "=== night sweep ${STAMP}: environment snapshot ==="
{
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "git_commit=$(git rev-parse HEAD)"
  echo "git_status=$(git status --porcelain -uno | wc -l) modified tracked files (must be 0)"
  uname -a
  grep -m1 "model name" /proc/cpuinfo
  grep MemTotal /proc/meminfo
  gcc --version | head -1
  cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || true
} | tee "${LOGDIR}/night_env_${STAMP}.log"

# Untracked files (night logs, raw CSVs) are expected during the sweep;
# the freeze requirement is that no TRACKED file is modified.
if [ "$(git status --porcelain -uno | wc -l)" -ne 0 ]; then
  echo "refusing to start: tracked files are modified (the freeze commit must be exact)" >&2
  exit 1
fi

echo "=== phase 1: instances ==="
[ -d instances/campaign_b ] || ${GEN_RANDOM} --output instances/campaign_b \
  --sizes 100,200,300,400,500,600,700,800,900,1000 --densities 0.3,0.6,0.9,1.0 --topology gen --seeds 10
[ -d instances/campaign_c ] || ${GEN_RANDOM} --output instances/campaign_c \
  --sizes 10000,20000,30000,40000,50000,60000,70000,80000,90000,100000 --densities 0.3,0.6,0.9,1.0 --topology gen --seeds 10
for shape in path binary star; do
  [ -d instances/campaign_d_${shape} ] || ${GEN_STRUCT} --output instances/campaign_d_${shape} \
    --shape ${shape} --sizes 100,200,500,1000,2000,5000,10000,20000,50000,100000 --seeds 10
done
for topo in in out; do
  mkdir -p "instances/campaign_e_${topo}"   # find on a missing dir would trip pipefail
  count=$(find "instances/campaign_e_${topo}" -maxdepth 1 -type f -name '*.pcf' -printf . | wc -c)
  if [ "${count}" -ne 4800 ]; then
    # deterministic generator: rerunning completes a partial directory
    ${GEN_RANDOM} --output instances/campaign_e_${topo} \
      --sizes 100,200,300,400,500,600,700,800,900,1000,10000,20000,30000,40000,50000,60000,70000,80000,90000,100000 \
      --densities 0.3,0.6,0.9,1.0 --topology ${topo} --seeds 10
  fi
done

link_subset() { # link_subset <src-dir> <dst-dir> <pattern-prefix> <sizes...>
  local src=$1 dst=$2 prefix=$3; shift 3
  rm -rf "${dst}"; mkdir -p "${dst}"
  local n
  for n in "$@"; do
    find "${src}" -maxdepth 1 -name "${prefix}${n}_*" -exec ln -sf "$(pwd)/{}" "${dst}/" \;
  done
}
link_subset instances/campaign_c instances/campaign_c_n10000_subset gen_n 10000
link_subset instances/campaign_c instances/campaign_c_n20000_subset gen_n 20000
link_subset instances/campaign_d_path   instances/campaign_d_path_pac_subset   path_n   100 200 500 1000 2000
link_subset instances/campaign_d_binary instances/campaign_d_binary_pac_subset binary_n 100 200 500 1000 2000
link_subset instances/campaign_d_star   instances/campaign_d_star_small        star_n   100 200 500 1000 2000 5000 10000 20000
link_subset instances/campaign_d_star   instances/campaign_d_star_large_only   star_n   50000 100000

echo "=== phase 1: manifests (build if missing, verify always) ==="
for dir in campaign_b campaign_c campaign_d_path campaign_d_binary campaign_d_star campaign_e_in campaign_e_out; do
  manifest=instances/manifests/${dir}.json
  [ -f "${manifest}" ] || python3 tools/build_instance_manifest.py --instances "instances/${dir}" --output "${manifest}"
  python3 tools/build_instance_manifest.py --instances "instances/${dir}" --verify "${manifest}"
done

echo "=== phase 2: launching lanes ==="
lane() { # lane <name> <core> <command...>
  local name=$1 core=$2; shift 2
  echo "lane ${name} (core ${core}): $*"
  PCF_CORE=${core} "$@" > "${LOGDIR}/night_${name}_${STAMP}.log" 2>&1 &
  echo "$! ${name}" >> "${LOGDIR}/night_pids_${STAMP}.txt"
}

: > "${LOGDIR}/night_pids_${STAMP}.txt"
lane official_bc 0  tools/run_official_campaigns.sh b c
lane dual_bcd    2  tools/run_dual_variant_campaigns.sh b c d
lane official_dg 4  bash -c 'tools/run_official_campaigns.sh d && \
  taskset -c 4 python3 tools/run_bppf_native_campaign.py \
    --pcf-solve build/pcf_solve --pcf-benchmark build/pcf_benchmark \
    --pcf-bppf build/pcf_bppf --pcf-bppf-oracle build/pcf_bppf_oracle \
    --instances instances/campaign_b \
    --output results/raw/campaign_g_bppf_native.csv \
    --repetitions 5 --prec 6'
lane official_ein  6  tools/run_official_campaigns.sh e_in
lane official_eout 8  tools/run_official_campaigns.sh e_out
lane dual_e        10 tools/run_dual_variant_campaigns.sh e

echo "=== waiting for all lanes (pids in ${LOGDIR}/night_pids_${STAMP}.txt) ==="
fail=0
while read -r pid name; do
  if wait "${pid}"; then
    echo "lane ${name}: OK"
  else
    echo "lane ${name}: FAILED (see ${LOGDIR}/night_${name}_${STAMP}.log)"
    fail=1
  fi
done < "${LOGDIR}/night_pids_${STAMP}.txt"

echo "=== night sweep finished: $(date -u +%FT%TZ), fail=${fail} ==="
exit "${fail}"

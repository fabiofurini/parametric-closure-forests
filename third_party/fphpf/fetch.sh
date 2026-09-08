#!/usr/bin/env bash
# Fetch Hochbaum's fully parametric HPF solver and apply this repository's
# two format-only changes.
#
# The solver's source is NOT redistributed here: it is downloaded from its own
# repository at the pinned commit below, so it always reaches you from its
# authors, under their licence. This script only places it where CMake expects
# it and changes two printf format strings (see UPSTREAM_README.md and
# local.patch). Run it once before building the pcf_fphpf target; only the
# campaign-H comparison needs it, nothing else in this repository does.
set -euo pipefail
cd "$(dirname "$0")"

UPSTREAM=https://github.com/hochbaumGroup/pseudoflow-parametric-cut-v2.git
COMMIT=fbd480fb1c4215792768b2a22f01d731a9fb6a27

if [ -f c/hpf.c ] && [ -f core/libhpf.c ]; then
  echo "already present (c/hpf.c, core/libhpf.c); delete c/ and core/ to re-fetch"
  exit 0
fi

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
echo "=== cloning $UPSTREAM at $COMMIT ==="
git -C "$TMP" init -q .
git -C "$TMP" remote add origin "$UPSTREAM"
git -C "$TMP" fetch -q --depth 1 origin "$COMMIT"
git -C "$TMP" checkout -q FETCH_HEAD

mkdir -p c core
cp "$TMP/src/pseudoflow/c/hpf.c"        c/hpf.c
cp "$TMP/src/pseudoflow/core/libhpf.c"  core/libhpf.c
cp "$TMP/src/pseudoflow/core/libhpf.h"  core/libhpf.h
cp "$TMP/LICENSE.md"                    LICENSE.md

echo "=== applying the two format changes recorded in local.patch ==="
# 1. timing line printed with 9 decimals instead of 3
sed -i 's|fprintf(f, "t %.3lf %.3lf %.3lf\\n", times\[0\], times\[1\], times\[2\]);|fprintf(f, "t %.9lf %.9lf %.9lf\\n", times[0], times[1], times[2]);|' c/hpf.c
# 2. per-group parameter printed with 17 significant digits instead of %lf's 6 decimals
sed -i 's|fprintf(f, "l %lf ", clam);|fprintf(f, "l %.17g ", clam);|' c/hpf.c

# Fail loudly if either line is not exactly as expected.
grep -q 'fprintf(f, "t %.9lf %.9lf %.9lf\\n", times\[0\], times\[1\], times\[2\]);' c/hpf.c \
  || { echo "ERROR: timing-format change did not apply" >&2; exit 1; }
grep -q 'fprintf(f, "l %.17g ", clam);' c/hpf.c \
  || { echo "ERROR: parameter-format change did not apply" >&2; exit 1; }
echo "=== verified; build with: cmake -S . -B build && cmake --build build --target pcf_fphpf ==="

# Test report — 2026-08-31 (pre-freeze for the V3 sweep)

Point-in-time correctness verification record for the freeze commit of
`docs/EXPERIMENTAL_PLAN_V3.md` (Phase 0). Not an experimental-results table.

## Machine and toolchain

- Host: Linux 6.8.0-138-generic, x86_64 (Ubuntu 22.04.5).
- CPU: Intel Core i7-12700; 20 logical CPUs visible; 32 GiB RAM.
- Compiler: GCC 11.4.0. CMake 3.22.1.

## Commands and outcome

```bash
# Release
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/pcf_tests                       # -> "pcf tests passed"

# Debug + AddressSanitizer/UndefinedBehaviorSanitizer
cmake -S . -B build-asan -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer"
cmake --build build-asan -j
./build-asan/pcf_tests                  # -> "pcf tests passed", exit 0
```

Both runs passed with zero sanitizer diagnostics. The suite covers, among
the rest (`tests/test_main.cpp`):

- the exhaustive closure-enumeration oracle on every directed forest with
  at most four vertices over a finite coefficient grid;
- 10,000 deterministic random forests up to 11 vertices, plus per-size
  random differential sweeps up to n=500;
- mixed-orientation path, balanced binary and star trees up to 257 vertices;
- 6,000 deterministic in-forest and 6,000 out-forest instances (plus 2,000
  larger per orientation) against HIPaC/HOPaC as applicable;
- bit-identical sequence agreement across pac, dpac, hpac (bounded-rebuild
  heap, the official implementation), dhpac (same rebuild policy),
  hpac_lazy (the original push-only lazy-deletion reference), hpac_eager,
  and rac.

## Pipeline preflight (same session)

`tools/run_benchmark.py` → `tools/validate_raw_data.py` →
`tools/aggregate_results.py` → `tools/emit_latex_tables.py` executed
end-to-end on `instances/tiny` (24 instances × 5 algorithms × 2
repetitions): no schema violations, 0 cross-algorithm mismatches, ratio
table emitted.

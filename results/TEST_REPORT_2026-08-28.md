# Test report — 2026-08-28

## Machine and toolchain

- Host: `canarino`, Linux 6.8.0-138-generic, x86_64.
- CPU: Intel Core i7-12700; 20 logical CPUs visible.
- Compiler: GCC 11.4.0.
- CMake: 3.22.1.

## Commands and outcome

```bash
cmake -S . -B /tmp/pcf-build-release -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/pcf-build-release -j2
ctest --test-dir /tmp/pcf-build-release --output-on-failure

cmake -S . -B /tmp/pcf-build-rac -DCMAKE_BUILD_TYPE=Debug
cmake --build /tmp/pcf-build-rac -j2
ctest --test-dir /tmp/pcf-build-rac --output-on-failure
```

Both runs passed. The CTest executable covers:

- PaC/DPaC/HPaC/DHPaC/RaC agreement on a mixed-orientation tree;
- exhaustive directed forests up to four items, all profits in `{-1,0,1}` and
  all weights in `{1,2}`;
- an independent closure-enumeration oracle on every exhaustive instance: it
  verifies the proposed prefix at every returned breakpoint and in every open
  interval between consecutive breakpoints;
- exhaustive agreement of PaC, DPaC, HPaC and DHPaC on directed forests up to
  four items, with the independent closure-enumeration oracle;
- 10,000 deterministic random directed forests up to 11 items checked by the
  oracle, and 2,000 random directed forests up to 100 items checked against
  HPaC;
- mixed-orientation path, balanced binary and star trees up to 257 items;
- 6,000 deterministic out-forest instances checked by the oracle, plus 2,000
  larger out-forest instances, comparing DHPaC, HPaC and the specialized HOPaC;
- closure layer partition, strict ratio order and closure-prefix invariants.

AddressSanitizer and UndefinedBehaviorSanitizer are also run on this machine.
They pass with `ASAN_OPTIONS=detect_leaks=0`. LeakSanitizer itself cannot run in
the controlled execution environment because it reports that it is under ptrace.

This report is a verification record, not an experimental-results table for the
paper.

# Reproducing this report

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure   # correctness gate
tools/run_night_sweep.sh                     # all campaigns, one command
tools/build_report.sh                        # aggregate + emit all tables
cd report && latexmk -pdf computational_report.tex
```

Code, generators, raw and processed data: <https://github.com/fabiofurini/parametric-closure-forests>, release `v0.3.0` (instance archives split under GitHub's asset size limit, with SHA-256 checksums). The pseudoflow baseline is the unmodified upstream implementation at <https://github.com/hochbaumGroup/Bounded-precision-simple-parametric.git>.

---

← [Per-family detail at every size](14-per-family-detail-at-every-size.md) · [Contents](README.md)

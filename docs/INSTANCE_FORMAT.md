# The `.pcf` instance format

One parametric maximum-closure instance per file. Grammar (whitespace
including newlines is insignificant between tokens):

```text
pcf 1
n <n>
profits <p_1> ... <p_n>
weights <w_1> ... <w_n>
arcs <m>
<u_1> <v_1>
...
<u_m> <v_m>
```

- `pcf 1` is a fixed magic header; `1` is the format version. A parser must
  reject any other version rather than guess a fallback grammar.
- `n` is the number of items, `n >= 1`.
- `profits` lists `p_i`, one signed 64-bit integer per item, 1-indexed by
  position (the first value is item 1's profit).
- `weights` lists `w_i`, one *strictly positive* 64-bit integer per item,
  same 1-indexing. `w_i <= 0` is invalid and every reader must reject it.
- `arcs` gives the arc count `m >= 0`, followed by `m` lines `u v` with
  1-based item identifiers. Arc `u v` means the closure implication
  `x_u <= x_v` ("`u` selected implies `v` selected"). Both endpoints must be
  in `[1, n]`, `u != v`, and no `(u, v)` pair may repeat.
- The underlying undirected graph must be a forest (no cycle in the
  undirected sense, not only in the directed sense) for every algorithm
  except where an algorithm's own documentation states it accepts general
  DAGs; arc orientation is otherwise arbitrary — it need not point away from
  or towards a single root, and in-forest/out-forest/mixed-forest are all
  legal.
- Total absolute profit and total weight must each stay within
  `INT64_MAX / 4` (`pcf::validate_instance`, `src/instance.cpp`) so every
  downstream 128-bit product used for exact rational comparisons is safe
  from overflow; instances near this bound are rejected explicitly rather
  than silently wrapping.
- No capacity field exists anywhere in this format. A reader must not accept
  one.
- Comments: none in format version 1. A future version may add a `#`-prefixed
  comment convention; readers must not accept `#` lines under `pcf 1`.
- No metadata (topology, coefficient family, seed) is stored inside the
  file. That information lives in the filename convention
  (`docs/EXPERIMENTAL_PROTOCOL.md`) and in the per-directory manifest
  (`instances/manifests/*.json`, built by `tools/build_instance_manifest.py`).

## Worked example

```text
pcf 1
n 4
profits 10 -3 8 2
weights 2 1 4 1
arcs 3
1 2
3 2
4 3
```

Four items; arcs mean `1∈X⇒2∈X`, `3∈X⇒2∈X`, `4∈X⇒3∈X`. This file is
committed at `instances/mixed_tree.pcf` and is the fixed regression fixture
used across the test suite documentation.

## CLI

```text
pcf_solve --instance FILE --algorithm fma|dfma|hfma|dhfma|hima|homa|rac [--output FILE]
```

`pcf_solve` prints the full macroitem sequence: node membership, cumulative
profit/weight and the exact `P/W` ratio of every macroitem, in non-increasing
ratio order. No capacity flag exists; passing one is a usage error.

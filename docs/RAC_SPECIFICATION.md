# RaC: specification to implementation traceability

This document freezes the implementation contract for `RaC` before its source
is accepted for experiments.  It is derived from the RaC section of the
accompanying manuscript, "On parametric Maximum Closure Problems over
precedence forests" (Dose, Furini, Locatelli), in particular the definitions
of cluster, the functions \(f_{\mathcal C}^\sigma\), `Compress1`, `Compress2`,
`Rake`, and the bottom-up/top-down phases.  It does not alter the manuscript,
which is maintained in a separate repository.

## Input and output

- Input: an acyclic directed forest with integral profits \(p_i\) and
  strictly positive integral weights \(w_i\).  An arc \((i,j)\) means
  \(x_i \leq x_j\).
- Output: the complete sequence of macroitems, in non-increasing exact
  threshold order. Equal thresholds belong to one macroitem.
- The implementation must support arbitrary orientations of the underlying
  forest and solve each connected component independently.
- All breakpoint and threshold comparisons are exact signed-64-bit rationals
  compared with signed-128-bit products.  Floating point values are forbidden
  in the algorithmic path.

## Required correspondence with the manuscript

| Manuscript object/operation | Required C++ representation and behavior |
| --- | --- |
| Cluster \((C,\partial\mathcal C)\), with border size at most two | `Cluster`, its boundary and four state-indexed envelopes; infeasible border states remain infeasible. |
| \(f_{\mathcal C}^\sigma\) | Exact upper envelope of affine lines `P - lambda W`; every line records aggregate profit and weight. |
| `Compress1` | Unary internalization: maximize over the state of the removed border vertex, adding its affine contribution exactly once. |
| `Compress2` | Join two 2-clusters at their common border vertex; maximize over that state and add the vertex contribution exactly once when it becomes internal. |
| `Rake` | Join all detached 1-clusters at a common surviving border with the backbone cluster; state-compatible envelopes are summed. |
| Bottom-up phase | Build a balanced rake-and-compress cluster hierarchy; it computes only the `f` functions and does not form macroitems. |
| Top-down phase | Traverse the hierarchy from the root, recover each item threshold from the two fixed-state envelopes, then group equal thresholds into macroitems. |

An implementation may use degree-three expansion with zero-cost equality edges
as an internal representation.  This is permitted only because it preserves
the feasible closures and objective exactly; original vertices must retain one
and only one objective-bearing copy, and the public result must contain only
original vertex identifiers.

## Acceptance tests

RaC is eligible for benchmarks only if all of the following pass:

1. unit tests for exact envelope sum, maximum, infeasible states and ties;
2. fixed hand-checked examples for `Compress1`, `Compress2`, `Rake`, paths,
   stars, mixed orientations, isolated nodes and multiple components;
3. exhaustive comparison with FMA on all directed forests up to the declared
   small size and a finite coefficient grid;
4. randomized differential comparison with FMA, including structured path,
   binary and star families;
5. structural checks: each returned macroitem is a closure increment, macroitems
   partition the original vertices, and thresholds are non-increasing;
6. sanitizer-enabled CTest run with no error.

The current archived `top_tree_cpp_experiment_package` is evidence and a source
to audit, not an accepted dependency.  Its code must be imported, adapted and
passed through the checks above inside this independent repository.

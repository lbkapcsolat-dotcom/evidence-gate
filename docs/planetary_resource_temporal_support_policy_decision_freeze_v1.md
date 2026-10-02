# Temporal Support Policy Decision Freeze V1

This gate freezes the temporal-support architecture after exact native
30-minute replacement discovery ended in a bounded HOLD.

Pinned predecessor receipt:

`55fdd516a583bed690f728096edf901ff9763a810605d0c26ce10f5b58f89deb`

The Elexon 30-minute source remains frozen and exact for
`2026-09-30T12:00:00Z -> 2026-09-30T12:30:00Z`.

Exactly two temporal-policy paths are permitted.

## PATH_A

`EXACT_NATIVE_INTERVALS_ONLY`

This is the current fail-closed continuity state.

- natural gas remains HOLD;
- freshwater remains HOLD;
- source search is off by default;
- three-source value composition remains blocked.

PATH_A does not mean that future explicit source discovery is impossible. It
means no further source search occurs by default or implicitly.

## PATH_B

`EXPLICIT_SOURCE_SUPPORT_TO_TARGET_WINDOW_OPERATOR`

PATH_B is declared but not activated. It can only be opened by a separate
explicit successor gate that first defines formal temporal semantics for the
operator.

The future operator must be predeclared and auditable. Before that formal gate:

- no silent downscaling;
- no interpolation;
- no imputation;
- no assumed constancy;
- no value composition.

There is no implicit third path, automatic path transition, or automatic
PATH_B activation.

Verdict:

`PASS_BOUNDED_TEMPORAL_SUPPORT_POLICY_DECISION_FREEZE`

This PASS freezes policy structure only. It does not admit PATH_B, perform
value composition, alter the frozen mathematical core, score the system, admit
runtime use, promote pointers, globally bind, or merge.

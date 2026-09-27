# Equilibrium Bridge Reconstructed Reproof V1 Implementation Plan

> **For agentic workers:** Execute task-by-task; every PASS requires a fresh command/result.

**Goal:** Reconstruct a new-source-identity Lean/mathlib proof kernel from A3665/BOOT2286 without impersonating the lost historical source bytes.

**Architecture:** Preserve A3664 receipts as historical targets only. Reconstruct the finite 6-bit Galois pair and cubical negative controls as provider-native Lean computations, then reconstruct the filtered relative pair and advance H4 only when a fresh proof closes. All reconstructed sources receive new identities and SHA256 values.

**Tech Stack:** Lean 4.34.0, mathlib commit db00fb3901b1bb4954f8a2373285959a5930bbfa, Lake, GitHub Actions standard ubuntu-latest.

## Global Constraints

- Historical source SHA values e6bc1119... and 60b1909e... are provenance anchors only.
- No historical SHA impersonation.
- Preserve the strict cubical failure as 6 of 192 negative controls.
- Zero sorry, admit, or axiom declarations in reconstructed Lean source.
- No global bind, runtime admission, model admission, or production promotion.
- ZERO_SPEND: public repository plus standard GitHub-hosted runner only.
- H4 induced-isomorphism PASS requires a fresh formal/computational proof; historical receipt values alone are insufficient.

---

### Task 1: Reconstructed finite Galois kernel and cubical regression

**Files:**
- Create: `ReconstructedOrderComplex.lean`
- Create: `ReconstructedHarness.lean`
- Modify: `lakefile.toml`
- Modify: `lean-toolchain`
- Modify: `.github/workflows/equilibrium-bridge-lean.yml`

**Interfaces:**
- Consumes: reconstructed six Boolean genomic/system coordinates and historical target metrics.
- Produces: `galois_adjunction`, monotonicity, unit/counit, fiber cardinality, 192-edge count, six strict-cubical counterexamples.

- [ ] Establish RED with harness theorem surface absent.
- [ ] Implement minimum reconstructed kernel.
- [ ] Obtain fresh Lean build PASS.
- [ ] Proof-escape scan returns zero hits.
- [ ] Record fresh source SHA256.

### Task 2: Filtered relative pair reconstruction

**Files:**
- Create: `ReconstructedRelativePair.lean`

**Interfaces:**
- Consumes: `phi`, finite poset orders, reconstructed image/preimage sets.
- Produces: A_S=30, K_S=31, A_G=60, K_G=61 and relative chain counts G=(1,60,480,1260,1320,480), S=(1,30,150,240,120,0).

- [ ] Prove pair cardinalities by native finite computation.
- [ ] Prove chain counts by recursive strict-chain enumeration.
- [ ] Keep H4 claim HOLD until boundary-rank proof is fresh.

### Task 3: Relative H4 and induced map

**Files:**
- Create: `ReconstructedRelativeH4.lean`

**Interfaces:**
- Consumes: reconstructed relative chain bases and normalized phi chain map.
- Produces only after proof: rank d4_G=839, rank d5_G=480, rank d4_S=119, rank d5_S=0; H4_G=H4_S=1; induced phi* nonzero and hence isomorphism.

- [ ] Implement/check F2 boundary matrices.
- [ ] Verify historical rank targets from reconstructed objects.
- [ ] Prove induced map nonzero on a non-boundary generator.
- [ ] Promote H4 only after fresh Lean build.

### Task 4: Final verification and receipt

**Files:**
- Create: `RECONSTRUCTED_REPROOF_V1_RECEIPT.json`

- [ ] Run fresh full build.
- [ ] Scan for forbidden proof escapes.
- [ ] Hash reconstructed sources and pin files.
- [ ] Record CI run/commit identities.
- [ ] Preserve any unresolved H4 item as HOLD, never inferred PASS.

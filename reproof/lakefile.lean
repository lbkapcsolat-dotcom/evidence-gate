import Lake
open Lake DSL

package equilibrium_bridge_reconstructed_reproof where

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @
  "db00fb3901b1bb4954f8a2373285959a5930bbfa"

lean_lib EquilibriumReproof where
  roots := #[`ReconstructedBridge, `ReconstructedRelativeHomology, `ReproofHarness]

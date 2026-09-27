import ReconstructedBridge
import ReconstructedRelativeHomology
import HistoricalBridgeBitVecPrimitiveProofs
import HistoricalRelativePairProofs

namespace EquilibriumHistoricalEquivalence

abbrev B6 := BitVec 6

def hb (n : Nat) : B6 := AlphaFull6D.BridgeBV.c n
def hr (n : Nat) : B6 := AlphaFull6D.RelativePair.c n

def rPhiB (x : B6) : B6 := BitVec.ofNat 6 (EquilibriumReproof.phi x.toNat)
def rLB (x : B6) : B6 := BitVec.ofNat 6 (EquilibriumReproof.L x.toNat)
def rLeq6 (a b : B6) : Prop := EquilibriumReproof.leB a.toNat b.toNat = true
def rTop : B6 := BitVec.ofNat 6 63

def phiExactCheck : Bool :=
  (List.range 64).all fun x =>
    (AlphaFull6D.BridgeBV.phi (hb x)).toNat == EquilibriumReproof.phi x

def LExactCheck : Bool :=
  (List.range 64).all fun x =>
    (AlphaFull6D.BridgeBV.L (hb x)).toNat == EquilibriumReproof.L x

def historicalLeB (a b : Nat) : Bool :=
  (BitVec.and (hb a) (BitVec.not (hb b))).toNat == 0

def orderExactCheck : Bool :=
  (List.range 64).all fun a =>
    (List.range 64).all fun b =>
      historicalLeB a b == EquilibriumReproof.leB a b

theorem phi_64_of_64_exact : phiExactCheck = true := by native_decide
theorem L_64_of_64_exact : LExactCheck = true := by native_decide
theorem order_relation_4096_of_4096_exact : orderExactCheck = true := by native_decide

theorem reconstructed_unit_naturality_exact :
    ∀ a b : B6, rLeq6 a b →
      rLeq6 (rPhiB (rLB a)) (rPhiB (rLB b)) ∧
      rLeq6 a (rPhiB (rLB b)) := by
  native_decide

theorem reconstructed_counit_naturality_exact :
    ∀ a b : B6, rLeq6 a b →
      rLeq6 (rLB (rPhiB a)) (rLB (rPhiB b)) ∧
      rLeq6 (rLB (rPhiB a)) b := by
  native_decide

theorem reconstructed_fiber_semantic_safety_exact :
    ∀ a b : B6, rPhiB a = rPhiB b →
      (a = rTop ↔ b = rTop) := by
  native_decide

def histInSK (x : Nat) : Bool := AlphaFull6D.RelativePair.inSKB (hr x)
def histInSA (x : Nat) : Bool := AlphaFull6D.RelativePair.inSAB (hr x)
def histInGK (x : Nat) : Bool := AlphaFull6D.RelativePair.inGKB (hr x)
def histInGA (x : Nat) : Bool := AlphaFull6D.RelativePair.inGAB (hr x)

def reconInSK (x : Nat) : Bool := EquilibriumReproof.K_S.contains x
def reconInSA (x : Nat) : Bool := EquilibriumReproof.A_S.contains x
def reconInGK (x : Nat) : Bool := EquilibriumReproof.K_G.contains x
def reconInGA (x : Nat) : Bool := EquilibriumReproof.A_G.contains x

def relativePairExactCheck : Bool :=
  (List.range 64).all fun x =>
    histInSK x == reconInSK x &&
    histInSA x == reconInSA x &&
    histInGK x == reconInGK x &&
    histInGA x == reconInGA x

theorem relative_pair_membership_64_of_64_exact :
    relativePairExactCheck = true := by native_decide

#check AlphaFull6D.BridgeBV.galois_adjunction
#check AlphaFull6D.BridgeBV.phi_monotone
#check AlphaFull6D.BridgeBV.L_monotone
#check AlphaFull6D.BridgeBV.unit
#check AlphaFull6D.BridgeBV.counit
#check AlphaFull6D.BridgeBV.unit_naturality
#check AlphaFull6D.BridgeBV.counit_naturality
#check AlphaFull6D.BridgeBV.fiber_semantic_safety

#check AlphaFull6D.RelativePair.galois_adjunction
#check AlphaFull6D.RelativePair.phi_maps_GK_to_SK
#check AlphaFull6D.RelativePair.phi_maps_GA_to_SA
#check AlphaFull6D.RelativePair.L_maps_SK_to_GK
#check AlphaFull6D.RelativePair.L_maps_SA_to_GA
#check AlphaFull6D.RelativePair.filtration_pullback_exact
#check AlphaFull6D.RelativePair.phi_preserves_level0
#check AlphaFull6D.RelativePair.phi_preserves_level1

#check EquilibriumReproof.cubical_negative_regression_exact
#check EquilibriumReproof.relative_certificate
#check EquilibriumReproof.induced_H4_isomorphism_bounded

end EquilibriumHistoricalEquivalence

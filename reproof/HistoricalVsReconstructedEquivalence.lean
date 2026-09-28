import ReconstructedBridge
import ReconstructedRelativeHomology
import HistoricalBridgeBitVecPrimitiveProofs
import HistoricalRelativePairProofs

namespace EquilibriumHistoricalEquivalence

abbrev B6 := BitVec 6

def hb (n : Nat) : B6 := AlphaFull6D.BridgeBV.c n
def hr (n : Nat) : B6 := AlphaFull6D.RelativePair.c n

def histPhiN (x : Nat) : Nat := (AlphaFull6D.BridgeBV.phi (hb x)).toNat
def histLN (x : Nat) : Nat := (AlphaFull6D.BridgeBV.L (hb x)).toNat
def reconPhiN (x : Nat) : Nat := EquilibriumReproof.phi x
def reconLN (x : Nat) : Nat := EquilibriumReproof.L x

def phiExactCheck : Bool :=
  (List.range 64).all fun x =>
    histPhiN x == reconPhiN x

def LExactCheck : Bool :=
  (List.range 64).all fun x =>
    histLN x == reconLN x

def historicalLeB (a b : Nat) : Bool :=
  (BitVec.and (hb a) (BitVec.not (hb b))).toNat == 0

def orderExactCheck : Bool :=
  (List.range 64).all fun a =>
    (List.range 64).all fun b =>
      historicalLeB a b == EquilibriumReproof.leB a b

def histUnitSig (a b : Nat) : Bool :=
  (! historicalLeB a b) ||
    (historicalLeB (histPhiN (histLN a)) (histPhiN (histLN b)) &&
     historicalLeB a (histPhiN (histLN b)))

def reconUnitSig (a b : Nat) : Bool :=
  (! EquilibriumReproof.leB a b) ||
    (EquilibriumReproof.leB (reconPhiN (reconLN a)) (reconPhiN (reconLN b)) &&
     EquilibriumReproof.leB a (reconPhiN (reconLN b)))

def unitNaturalitySignatureExactCheck : Bool :=
  (List.range 64).all fun a =>
    (List.range 64).all fun b =>
      histUnitSig a b == reconUnitSig a b

def histCounitSig (a b : Nat) : Bool :=
  (! historicalLeB a b) ||
    (historicalLeB (histLN (histPhiN a)) (histLN (histPhiN b)) &&
     historicalLeB (histLN (histPhiN a)) b)

def reconCounitSig (a b : Nat) : Bool :=
  (! EquilibriumReproof.leB a b) ||
    (EquilibriumReproof.leB (reconLN (reconPhiN a)) (reconLN (reconPhiN b)) &&
     EquilibriumReproof.leB (reconLN (reconPhiN a)) b)

def counitNaturalitySignatureExactCheck : Bool :=
  (List.range 64).all fun a =>
    (List.range 64).all fun b =>
      histCounitSig a b == reconCounitSig a b

def histFiberSig (a b : Nat) : Bool :=
  (!(histPhiN a == histPhiN b)) || ((a == 63) == (b == 63))

def reconFiberSig (a b : Nat) : Bool :=
  (!(reconPhiN a == reconPhiN b)) || ((a == 63) == (b == 63))

def fiberSemanticSafetySignatureExactCheck : Bool :=
  (List.range 64).all fun a =>
    (List.range 64).all fun b =>
      histFiberSig a b == reconFiberSig a b

theorem phi_64_of_64_exact : phiExactCheck = true := by native_decide
theorem L_64_of_64_exact : LExactCheck = true := by native_decide
theorem order_relation_4096_of_4096_exact : orderExactCheck = true := by native_decide
theorem unit_naturality_signature_4096_of_4096_exact :
    unitNaturalitySignatureExactCheck = true := by native_decide
theorem counit_naturality_signature_4096_of_4096_exact :
    counitNaturalitySignatureExactCheck = true := by native_decide
theorem fiber_semantic_safety_signature_4096_of_4096_exact :
    fiberSemanticSafetySignatureExactCheck = true := by native_decide

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

end EquilibriumHistoricalEquivalencedef reconstructedUnitNaturalityExactCheck : Bool :=
  (List.range 64).all fun a =>
    (List.range 64).all fun b =>
      !(EquilibriumReproof.leB a b) ||
        (EquilibriumReproof.leB
            (EquilibriumReproof.phi (EquilibriumReproof.L a))
            (EquilibriumReproof.phi (EquilibriumReproof.L b)) &&
         EquilibriumReproof.leB a
            (EquilibriumReproof.phi (EquilibriumReproof.L b)))

def reconstructedCounitNaturalityExactCheck : Bool :=
  (List.range 64).all fun a =>
    (List.range 64).all fun b =>
      !(EquilibriumReproof.leB a b) ||
        (EquilibriumReproof.leB
            (EquilibriumReproof.L (EquilibriumReproof.phi a))
            (EquilibriumReproof.L (EquilibriumReproof.phi b)) &&
         EquilibriumReproof.leB
            (EquilibriumReproof.L (EquilibriumReproof.phi a)) b)

def reconstructedFiberSemanticSafetyExactCheck : Bool :=
  (List.range 64).all fun a =>
    (List.range 64).all fun b =>
      (EquilibriumReproof.phi a != EquilibriumReproof.phi b) ||
        ((a == 63) == (b == 63))

theorem reconstructed_unit_naturality_exact_4096 :
    reconstructedUnitNaturalityExactCheck = true := by native_decide

theorem reconstructed_counit_naturality_exact_4096 :
    reconstructedCounitNaturalityExactCheck = true := by native_decide

theorem reconstructed_fiber_semantic_safety_exact_4096 :
    reconstructedFiberSemanticSafetyExactCheck = true := by native_decide

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

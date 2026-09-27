import Mathlib
import ReconstructedBridge

namespace EquilibriumReproof

def K_S : List Nat := imageVertices.filter (fun x => x != 0)
def A_S : List Nat := imageVertices.filter (fun x => x != 0 && x != 63)
def K_G : List Nat := states.filter (fun x => phi x != 0)
def A_G : List Nat := states.filter (fun x => phi x != 0 && phi x != 63)

def relativeChain (A : List Nat) (ch : List Nat) : Bool :=
  !(ch.all (fun v => A.contains v))

def relativeChains (K A : List Nat) (n : Nat) : List (List Nat) :=
  (strictChains K (n + 1)).filter (relativeChain A)

def faceAt (ch : List Nat) (i : Nat) : List Nat := ch.eraseIdx i

def basisIndex (basis : List (List Nat)) (x : List Nat) : Nat :=
  basis.findIdx (fun y => y == x)

def boundaryColumn (K A : List Nat) (n : Nat) (ch : List Nat) : Nat :=
  if n == 0 then 0
  else
    let cod := relativeChains K A (n - 1)
    (List.range ch.length).foldl
      (fun acc i =>
        let f := faceAt ch i
        if relativeChain A f then
          acc ^^^ (2 ^ basisIndex cod f)
        else acc)
      0

def boundaryColumns (K A : List Nat) (n : Nat) : List Nat :=
  (relativeChains K A n).map (boundaryColumn K A n)

def pivot (x : Nat) : Nat := Nat.log2 x

def reduceVector (basis : List Nat) (v : Nat) : Nat :=
  basis.foldl (fun x p => if x.testBit (pivot p) then x ^^^ p else x) v

def insertPivot (v : Nat) : List Nat → List Nat
  | [] => [v]
  | p :: ps =>
      if pivot v > pivot p then v :: p :: ps
      else p :: insertPivot v ps

def rankStep (basis : List Nat) (v : Nat) : List Nat :=
  let r := reduceVector basis v
  if r == 0 then basis else insertPivot r basis

def gf2Rank (cols : List Nat) : Nat :=
  (cols.foldl rankStep []).length

structure PivotWitness where
  vec : Nat
  combo : Nat
  deriving Repr, BEq

def reduceWitness (basis : List PivotWitness) (vc : Nat × Nat) : Nat × Nat :=
  basis.foldl
    (fun acc p =>
      if acc.1.testBit (pivot p.vec) then
        (acc.1 ^^^ p.vec, acc.2 ^^^ p.combo)
      else acc)
    vc

def insertWitness (w : PivotWitness) : List PivotWitness → List PivotWitness
  | [] => [w]
  | p :: ps =>
      if pivot w.vec > pivot p.vec then w :: p :: ps
      else p :: insertWitness w ps

def kernelBasisAux :
    List Nat → Nat → List PivotWitness → List Nat → List Nat
  | [], _, _, kernel => kernel
  | v :: vs, i, basis, kernel =>
      let reduced := reduceWitness basis (v, 2 ^ i)
      if reduced.1 == 0 then
        kernelBasisAux vs (i + 1) basis (reduced.2 :: kernel)
      else
        let w : PivotWitness := { vec := reduced.1, combo := reduced.2 }
        kernelBasisAux vs (i + 1) (insertWitness w basis) kernel

def kernelBasis (cols : List Nat) : List Nat :=
  kernelBasisAux cols 0 [] []

def mappedChain (ch : List Nat) : List Nat := ch.map phi

def chainMapColumn (n : Nat) (ch : List Nat) : Nat :=
  let cod := relativeChains K_S A_S n
  let im := mappedChain ch
  if im.eraseDups.length != im.length then 0
  else 2 ^ basisIndex cod im

def chainMapColumns (n : Nat) : List Nat :=
  (relativeChains K_G A_G n).map (chainMapColumn n)

def applyLinear (cols : List Nat) (combo : Nat) : Nat :=
  let rec go : List Nat → Nat → Nat → Nat
    | [], _, acc => acc
    | c :: cs, i, acc =>
        go cs (i + 1) (if combo.testBit i then acc ^^^ c else acc)
  go cols 0 0

def boundaryCommutesAt (n : Nat) : Bool :=
  if n == 0 then true
  else
    let dS := boundaryColumns K_S A_S n
    let fPrev := chainMapColumns (n - 1)
    let fNow := chainMapColumns n
    let dG := boundaryColumns K_G A_G n
    (List.zip fNow dG).all
      (fun pair =>
        applyLinear dS pair.1 == applyLinear fPrev pair.2)

def relativeDims (K A : List Nat) : List Nat :=
  (List.range 6).map (fun n => (relativeChains K A n).length)

def boundaryRanks (K A : List Nat) : List Nat :=
  0 :: ((List.range 5).map (fun i => gf2Rank (boundaryColumns K A (i + 1))))

def H4dim (K A : List Nat) : Nat :=
  (relativeChains K A 4).length -
    gf2Rank (boundaryColumns K A 4) -
    gf2Rank (boundaryColumns K A 5)

def inducedH4Images : List Nat :=
  let cycles := kernelBasis (boundaryColumns K_G A_G 4)
  let f4 := chainMapColumns 4
  cycles.map (applyLinear f4)

def inducedH4Rank : Nat := gf2Rank inducedH4Images

def supportSize120 (x : Nat) : Nat :=
  ((List.range 120).filter (fun i => x.testBit i)).length

def nonzeroGeneratorImageSupports : List Nat :=
  ((inducedH4Images.filter (fun x => x != 0)).map supportSize120).eraseDups

theorem relative_certificate :
    (A_S.length = 30 ∧ K_S.length = 31 ∧ A_G.length = 60 ∧ K_G.length = 61) ∧
    (relativeDims K_G A_G = [1, 60, 480, 1260, 1320, 480] ∧
      relativeDims K_S A_S = [1, 30, 150, 240, 120, 0]) ∧
    (boundaryRanks K_G A_G = [0, 1, 59, 421, 839, 480] ∧
      boundaryRanks K_S A_S = [0, 1, 29, 121, 119, 0]) ∧
    ((List.range 5).all (fun i => boundaryCommutesAt (i + 1)) = true) ∧
    (H4dim K_G A_G = 1) ∧
    (H4dim K_S A_S = 1) ∧
    (inducedH4Rank = 1) ∧
    (nonzeroGeneratorImageSupports = [120]) := by
  native_decide

theorem pair_cardinalities :
    A_S.length = 30 ∧ K_S.length = 31 ∧
    A_G.length = 60 ∧ K_G.length = 61 :=
  relative_certificate.1

theorem relative_chain_dimensions :
    relativeDims K_G A_G = [1, 60, 480, 1260, 1320, 480] ∧
    relativeDims K_S A_S = [1, 30, 150, 240, 120, 0] :=
  relative_certificate.2.1

theorem relative_boundary_ranks :
    boundaryRanks K_G A_G = [0, 1, 59, 421, 839, 480] ∧
    boundaryRanks K_S A_S = [0, 1, 29, 121, 119, 0] :=
  relative_certificate.2.2.1

theorem relative_chain_map_commutes_dim_1_to_5 :
    (List.range 5).all (fun i => boundaryCommutesAt (i + 1)) = true :=
  relative_certificate.2.2.2.1

theorem relative_H4_G : H4dim K_G A_G = 1 :=
  relative_certificate.2.2.2.2.1

theorem relative_H4_S : H4dim K_S A_S = 1 :=
  relative_certificate.2.2.2.2.2.1

theorem induced_H4_rank_one : inducedH4Rank = 1 :=
  relative_certificate.2.2.2.2.2.2.1

theorem induced_H4_isomorphism_bounded :
    H4dim K_G A_G = 1 ∧
    H4dim K_S A_S = 1 ∧
    inducedH4Rank = 1 :=
  ⟨relative_H4_G, relative_H4_S, induced_H4_rank_one⟩

theorem induced_H4_generator_image_support :
    nonzeroGeneratorImageSupports = [120] :=
  relative_certificate.2.2.2.2.2.2.2

end EquilibriumReproof

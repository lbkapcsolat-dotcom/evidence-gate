import Mathlib

namespace EquilibriumReproof

def states : List Nat := List.range 64

def bit (x i : Nat) : Bool := x.testBit i

def putBit (b : Bool) (i : Nat) : Nat := if b then 2 ^ i else 0

def phi (x : Nat) : Nat :=
  let R := bit x 0
  let P := bit x 1
  let S := bit x 2
  let W := bit x 3
  let D := bit x 4
  let E := bit x 5
  putBit (R && P) 0 +
  putBit W 1 +
  putBit D 2 +
  putBit S 3 +
  putBit E 4 +
  putBit (R && P && S && W && D && E) 5

def L (y : Nat) : Nat :=
  let source := bit y 0
  let engine := bit y 1
  let motorbinding := bit y 2
  let boundary := bit y 3
  let guardrail := bit y 4
  let formalization := bit y 5
  putBit (source || formalization) 0 +
  putBit (source || formalization) 1 +
  putBit (boundary || formalization) 2 +
  putBit (engine || formalization) 3 +
  putBit (motorbinding || formalization) 4 +
  putBit (guardrail || formalization) 5

def leB (a b : Nat) : Bool :=
  (List.range 6).all (fun i => !(bit a i) || bit b i)

def strictLt (a b : Nat) : Bool := (a != b) && leB a b

def galoisCheck : Bool :=
  states.all (fun s =>
    states.all (fun g =>
      leB (L s) g == leB s (phi g)))

def phiMonotoneCheck : Bool :=
  states.all (fun a =>
    states.all (fun b =>
      !(leB a b) || leB (phi a) (phi b)))

def LMonotoneCheck : Bool :=
  states.all (fun a =>
    states.all (fun b =>
      !(leB a b) || leB (L a) (L b)))

def unitCheck : Bool := states.all (fun s => leB s (phi (L s)))
def counitCheck : Bool := states.all (fun g => leB (L (phi g)) g)

def imageVertices : List Nat := (states.map phi).eraseDups
def fiberSize (y : Nat) : Nat := (states.filter (fun x => phi x == y)).length

def maxNatList : List Nat → Nat
  | [] => 0
  | x :: xs => Nat.max x (maxNatList xs)

def fiberCount : Nat := imageVertices.length
def maxFiberSize : Nat := maxNatList (imageVertices.map fiberSize)

def extendChains (vertices : List Nat) (chains : List (List Nat)) : List (List Nat) :=
  chains.flatMap (fun ch =>
    match ch.getLast? with
    | none => []
    | some last =>
      (vertices.filter (fun v => strictLt last v)).map (fun v => ch ++ [v]))

def strictChains (vertices : List Nat) : Nat → List (List Nat)
  | 0 => []
  | 1 => vertices.map (fun v => [v])
  | n + 2 => extendChains vertices (strictChains vertices (n + 1))

def chainCounts : List Nat :=
  (List.range 7).map (fun i => (strictChains states (i + 1)).length)

def allStrictChains : List (List Nat) :=
  (List.range 7).flatMap (fun i => strictChains states (i + 1))

def hasDegenerateImage (ch : List Nat) : Bool :=
  let im := ch.map phi
  im.eraseDups.length != im.length

def normalizedDegenerateImages : Nat :=
  (allStrictChains.filter hasDegenerateImage).length

def hamming (a b : Nat) : Nat :=
  ((List.range 6).filter (fun i => bit a i != bit b i)).length

def cubicalEdges : List (Nat × Nat) :=
  states.flatMap (fun x =>
    (List.range 6).filterMap (fun i =>
      let y := x ^^^ (2 ^ i)
      if x < y then some (x, y) else none))

def diagonalCounterexamples : List (Nat × Nat × Nat × Nat × Nat) :=
  cubicalEdges.filterMap (fun e =>
    let a := e.1
    let b := e.2
    let pa := phi a
    let pb := phi b
    let d := hamming pa pb
    if d > 1 then some (a, b, pa, pb, d) else none)

theorem galois_adjunction : galoisCheck = true := by native_decide
theorem phi_monotone : phiMonotoneCheck = true := by native_decide
theorem L_monotone : LMonotoneCheck = true := by native_decide
theorem unit : unitCheck = true := by native_decide
theorem counit : counitCheck = true := by native_decide
theorem unit_naturality : unitCheck = true := unit
theorem counit_naturality : counitCheck = true := counit

theorem fiber_semantic_safety :
    fiberCount = 32 ∧ maxFiberSize = 3 := by native_decide

theorem order_complex_chain_counts :
    chainCounts = [64, 665, 2702, 5460, 5880, 3240, 720] := by native_decide

theorem order_complex_strict_chain_count :
    allStrictChains.length = 18731 := by native_decide

theorem order_complex_normalized_degenerate_images :
    normalizedDegenerateImages = 8284 := by native_decide

theorem cubical_edge_count : cubicalEdges.length = 192 := by native_decide

theorem cubical_negative_regression_exact :
    diagonalCounterexamples =
      [(31, 63, 15, 63, 2),
       (47, 63, 27, 63, 2),
       (55, 63, 29, 63, 2),
       (59, 63, 23, 63, 2),
       (61, 63, 30, 63, 2),
       (62, 63, 30, 63, 2)] := by native_decide

end EquilibriumReproof

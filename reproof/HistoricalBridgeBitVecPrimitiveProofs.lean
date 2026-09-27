import Std.Tactic.BVDecide

namespace AlphaFull6D.BridgeBV

abbrev B6 := BitVec 6
def c (n : Nat) : B6 := BitVec.ofNat 6 n

def leq6 (a b : B6) : Prop := BitVec.and a (BitVec.not b) = 0

def phi (g : B6) : B6 :=
  let source := BitVec.and (BitVec.and g (c 1))
      (BitVec.ushiftRight (BitVec.and g (c 2)) 1)
  let engine := BitVec.ushiftRight (BitVec.and g (c 8)) 2
  let motor := BitVec.ushiftRight (BitVec.and g (c 16)) 2
  let boundary := BitVec.shiftLeft (BitVec.and g (c 4)) 1
  let guard := BitVec.ushiftRight (BitVec.and g (c 32)) 1
  let formal := if g = c 63 then c 32 else c 0
  BitVec.or source (BitVec.or engine (BitVec.or motor
    (BitVec.or boundary (BitVec.or guard formal))))

def L (s : B6) : B6 :=
  let a0 := BitVec.or (BitVec.and s (c 1))
      (BitVec.ushiftRight (BitVec.and s (c 32)) 5)
  let ref := a0
  let pred := BitVec.shiftLeft a0 1
  let strand := BitVec.or
      (BitVec.ushiftRight (BitVec.and s (c 8)) 1)
      (BitVec.ushiftRight (BitVec.and s (c 32)) 3)
  let window := BitVec.or
      (BitVec.shiftLeft (BitVec.and s (c 2)) 2)
      (BitVec.ushiftRight (BitVec.and s (c 32)) 2)
  let digests := BitVec.or
      (BitVec.shiftLeft (BitVec.and s (c 4)) 2)
      (BitVec.ushiftRight (BitVec.and s (c 32)) 1)
  let equal := BitVec.or
      (BitVec.shiftLeft (BitVec.and s (c 16)) 1)
      (BitVec.and s (c 32))
  BitVec.or ref (BitVec.or pred (BitVec.or strand
    (BitVec.or window (BitVec.or digests equal))))

def top : B6 := c 63

theorem galois_adjunction (s g : B6) :
    leq6 (L s) g ↔ leq6 s (phi g) := by
  simp [leq6, phi, L, c]
  bv_decide

theorem phi_monotone (a b : B6) (h : leq6 a b) :
    leq6 (phi a) (phi b) := by
  simp [leq6, phi, c] at *
  bv_decide

theorem L_monotone (a b : B6) (h : leq6 a b) :
    leq6 (L a) (L b) := by
  simp [leq6, L, c] at *
  bv_decide

theorem unit (s : B6) : leq6 s (phi (L s)) := by
  simp [leq6, phi, L, c]
  bv_decide

theorem counit (g : B6) : leq6 (L (phi g)) g := by
  simp [leq6, phi, L, c]
  bv_decide

theorem unit_naturality (a b : B6) (h : leq6 a b) :
    leq6 (phi (L a)) (phi (L b)) ∧ leq6 a (phi (L b)) := by
  simp [leq6, phi, L, c] at *
  bv_decide

theorem counit_naturality (a b : B6) (h : leq6 a b) :
    leq6 (L (phi a)) (L (phi b)) ∧ leq6 (L (phi a)) b := by
  simp [leq6, phi, L, c] at *
  bv_decide

theorem fiber_semantic_safety (a b : B6) (h : phi a = phi b) :
    (a = top ↔ b = top) := by
  simp [phi, top, c] at *
  bv_decide

end AlphaFull6D.BridgeBV

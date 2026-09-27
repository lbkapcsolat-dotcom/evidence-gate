import Std.Tactic.BVDecide

namespace AlphaFull6D.RelativePair

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

def inImageB (s : B6) : Bool :=
  (s == c 63) || (((BitVec.and s (c 32)) == c 0) && !((BitVec.and s (c 31)) == c 31))

def inSKB (s : B6) : Bool := inImageB s && !(s == c 0)
def inSAB (s : B6) : Bool := inImageB s && !(s == c 0) && !(s == c 63)

def inGKB (g : B6) : Bool := inSKB (phi g)
def inGAB (g : B6) : Bool := inSAB (phi g)

def fS (s : B6) : Nat := if inSAB s then 0 else if inSKB s then 1 else 2
def fG (g : B6) : Nat := fS (phi g)

theorem galois_adjunction (s g : B6) :
    leq6 (L s) g ↔ leq6 s (phi g) := by
  simp [leq6, phi, L, c]
  bv_decide

theorem phi_maps_GK_to_SK (g : B6) (h : inGKB g = true) : inSKB (phi g) = true := h
theorem phi_maps_GA_to_SA (g : B6) (h : inGAB g = true) : inSAB (phi g) = true := h

theorem L_maps_SK_to_GK (s : B6) (h : inSKB s = true) : inGKB (L s) = true := by
  simp [inGKB, inSKB, inImageB, phi, L, c] at *
  bv_decide

theorem L_maps_SA_to_GA (s : B6) (h : inSAB s = true) : inGAB (L s) = true := by
  simp [inGAB, inSAB, inImageB, phi, L, c] at *
  bv_decide

theorem filtration_pullback_exact (g : B6) : fG g = fS (phi g) := rfl

theorem phi_preserves_level0 (g : B6) (h : fG g = 0) : fS (phi g) = 0 := by
  simpa [fG] using h

theorem phi_preserves_level1 (g : B6) (h : fG g ≤ 1) : fS (phi g) ≤ 1 := by
  simpa [fG] using h

end AlphaFull6D.RelativePair

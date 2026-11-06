import Lean

/-!
ESS_SZEGEDY_EXACT_LEAN_THEOREM_AND_EXTERNAL_SEMANTIC_WITNESS_V1
TOY_SYSTEM_V1, mathematical finite model only, no physical semantics.
TARGET TOOLCHAIN: leanprover/lean4:v4.35.0 (not verified at authoring time).
No sorry, no explicit new axioms, no native_decide, no automation from Mathlib.

Proof obligation: for x ∈ {0,1,2}, w ∈ {0,1},
  u = 0 if x=0, otherwise u=1,
  next = x + w - u ∈ {0,1,2}.
The proof's exact validity remains HOLD until the stated kernel checks it.
-/

namespace ESS_Szegedy_ToyV1

/-- Controller uses current state only. -/
def policy (x : Fin 3) : Nat :=
  if x.val = 0 then 0 else 1

/-- Interpreted integer transition; avoids saturating Nat subtraction. -/
def rawStep (x : Fin 3) (w : Fin 2) : Int :=
  Int.ofNat x.val + Int.ofNat w.val - Int.ofNat (policy x)

/-- Explicit admissible state interval. -/
def insideK (y : Int) : Prop := 0 ≤ y ∧ y ≤ 2

/-- Standalone semantic transition table, intentionally not defined by rawStep. -/
def semanticNext (x : Fin 3) (w : Fin 2) : Fin 3 :=
  if x.val = 2 then
    (if w.val = 0 then 1 else 2)
  else
    (if w.val = 0 then 0 else 1)

/-- Main exact bounded invariant over six possible one-step cases. -/
theorem one_step_invariant :
    ∀ (x : Fin 3) (w : Fin 2), insideK (rawStep x w) := by
  decide

/-- Independent table agrees with integer transition on the declared domain. -/
theorem table_refines_arithmetic :
    ∀ (x : Fin 3) (w : Fin 2),
      Int.ofNat (semanticNext x w).val = rawStep x w := by
  decide

/-- Three-step safety: all disturbances are universally quantified. -/
theorem three_step_safety :
    ∀ (x₀ : Fin 3) (w₀ w₁ w₂ : Fin 2),
      insideK (rawStep x₀ w₀) ∧
      insideK (rawStep (semanticNext x₀ w₀) w₁) ∧
      insideK (rawStep (semanticNext (semanticNext x₀ w₀) w₁) w₂) := by
  decide

/-- Negative logical control: without u=1 at x=2, w=1 exits K. -/
theorem missing_control_counterexample :
    ¬ insideK ((2 : Int) + 1 - 0) := by
  decide

#print axioms one_step_invariant
#print axioms table_refines_arithmetic
#print axioms three_step_safety
#print axioms missing_control_counterexample

end ESS_Szegedy_ToyV1

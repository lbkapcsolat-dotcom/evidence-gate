import EquilibriumBridge

open EquilibriumBridge

def locked : EvidenceState :=
  { negative := false
    missingRequired := false
    commitBind := true
    byteBind := true
    exactMemberSet := true
    fourWayEquality := true
    remoteReadback := true }

example : readOnlyLock locked = true := by decide
example : admission locked = .pass := by decide
example : canPromote false = false := no_silent_promotion
#check negative_evidence_rejects
#check missing_required_holds
#check lock_implies_pass
#check promotion_requires_new_admissible_evidence
#check replay_deterministic

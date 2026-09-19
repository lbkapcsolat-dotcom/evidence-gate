namespace EquilibriumBridge

inductive Admission where
  | pass | hold | reject
  deriving DecidableEq, Repr

structure EvidenceState where
  negative : Bool
  missingRequired : Bool
  commitBind : Bool
  byteBind : Bool
  exactMemberSet : Bool
  fourWayEquality : Bool
  remoteReadback : Bool
  deriving DecidableEq, Repr

def admission (s : EvidenceState) : Admission :=
  if s.negative then .reject
  else if s.missingRequired then .hold
  else if s.commitBind && s.byteBind && s.exactMemberSet &&
          s.fourWayEquality && s.remoteReadback then .pass
  else .hold

def readOnlyLock (s : EvidenceState) : Bool :=
  s.commitBind && s.byteBind && s.exactMemberSet &&
  s.fourWayEquality && s.remoteReadback && !s.negative && !s.missingRequired

def canPromote (hasNewAdmissibleEvidence : Bool) : Bool :=
  hasNewAdmissibleEvidence

theorem negative_evidence_rejects (s : EvidenceState)
    (h : s.negative = true) : admission s = .reject := by
  simp [admission, h]

theorem missing_required_holds (s : EvidenceState)
    (hn : s.negative = false) (hm : s.missingRequired = true) :
    admission s = .hold := by
  simp [admission, hn, hm]

theorem lock_implies_pass (s : EvidenceState)
    (h : readOnlyLock s = true) : admission s = .pass := by
  simp [readOnlyLock] at h
  rcases h with ⟨hc, hb, hm, hf, hr, hn, hmiss⟩
  simp [admission, hc, hb, hm, hf, hr, hn, hmiss]

theorem no_silent_promotion :
    canPromote false = false := by
  rfl

theorem promotion_requires_new_admissible_evidence
    (newEvidence : Bool) (h : canPromote newEvidence = true) :
    newEvidence = true := by
  simpa [canPromote] using h

theorem replay_deterministic (s : EvidenceState) :
    admission s = admission s := by
  rfl

end EquilibriumBridge

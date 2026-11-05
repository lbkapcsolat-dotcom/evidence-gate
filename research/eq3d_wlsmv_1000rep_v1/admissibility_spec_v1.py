"""Proposed EQ3D fit admissibility and negative-control specification. Not adopted."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from math import isfinite
class FitState(str, Enum):
    ADMISSIBLE="ADMISSIBLE_DIAGNOSTIC"
    INADMISSIBLE="INADMISSIBLE"
    MISSING="INSUFFICIENT_EVIDENCE"
class ControlState(str, Enum):
    REJECT="REJECT_M3_CANDIDATE"
    NOT_REJECTED="M3_NOT_REJECTED_CANDIDATE"
    UNKNOWN="INDETERMINATE"
@dataclass(frozen=True)
class Evidence:
    converged: Optional[bool]
    covlv_min_eigen: Optional[float]
    covariance_inspected: bool=True
    finite_fit_measures: Optional[bool]=None
    critical_warning: Optional[bool]=None
    exact_provenance: bool=False

def assess_fit(e: Evidence) -> FitState:
    if not e.exact_provenance or e.converged is None or not e.covariance_inspected:
        return FitState.MISSING
    if not e.converged: return FitState.INADMISSIBLE
    if e.covlv_min_eigen is None or not isfinite(e.covlv_min_eigen):
        return FitState.MISSING
    if e.covlv_min_eigen<=0: return FitState.INADMISSIBLE
    if e.finite_fit_measures is None or e.critical_warning is None:
        return FitState.MISSING
    if not e.finite_fit_measures or e.critical_warning:
        return FitState.INADMISSIBLE
    return FitState.ADMISSIBLE

def assess_control(m3: FitState, alternative: FitState, disjoint: bool) -> ControlState:
    if not disjoint: return ControlState.UNKNOWN
    if m3==FitState.INADMISSIBLE and alternative==FitState.ADMISSIBLE:
        return ControlState.REJECT
    if m3==FitState.ADMISSIBLE and alternative==FitState.ADMISSIBLE:
        return ControlState.NOT_REJECTED
    return ControlState.UNKNOWN

"""Static, prospective-only EQ3D V1 design gate. NO model fitting or simulation."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

TRUTHS = ("M3", "M4", "M5", "M7")
ATTEMPTS_PER_TRUTH = 250
HISTORICAL_GRID_RUN = 41586168086
DEV_FIXTURE_RUN = 41983775160

class Comparison(str, Enum):
    ELIGIBLE_FOR_REVIEW = "ELIGIBLE_FOR_VERSION_PINNED_ROBUST_TEST_REVIEW"
    HOLD = "HOLD_COMPARISON_METHOD"

@dataclass(frozen=True)
class PairEvidence:
    exact_same_data: Optional[bool]
    same_ordered_variables: Optional[bool]
    same_estimator: Optional[bool]
    same_parameterization: Optional[bool]
    same_thresholds: Optional[bool]
    regular_nesting_proven: Optional[bool]
    both_numerically_admissible: Optional[bool]
    pinned_version_verified: Optional[bool]
    robust_method_supported: Optional[bool]
    boundary_or_nonregular: Optional[bool]

def comparison_preflight(p: PairEvidence) -> Comparison:
    """Eligibility for methodological review, never automatic p-value approval."""
    if all(v is True for v in (
        p.exact_same_data, p.same_ordered_variables, p.same_estimator,
        p.same_parameterization, p.same_thresholds,
        p.regular_nesting_proven, p.both_numerically_admissible,
        p.pinned_version_verified, p.robust_method_supported
    )) and p.boundary_or_nonregular is False:
        return Comparison.ELIGIBLE_FOR_REVIEW
    return Comparison.HOLD

def heldout_preflight(*, protocol_committed: bool, seed_schedule_hash: Optional[str],
                      independent_review: bool, bounded_authorization: bool,
                      original_grid_untouched: bool, original_grid_used_as_heldout: bool,
                      locked_analysis_plan: bool) -> bool:
    """Fail closed. True authorizes only consideration of a separately requested run."""
    return (protocol_committed and isinstance(seed_schedule_hash, str)
            and len(seed_schedule_hash) == 64
            and all(c in "0123456789abcdef" for c in seed_schedule_hash)
            and independent_review and bounded_authorization
            and original_grid_untouched and not original_grid_used_as_heldout
            and locked_analysis_plan)

def wilson_interval(successes: int, attempts: int, z: float=1.959963984540054):
    """Descriptive 95% interval, all-attempt denominator. Not admission by itself."""
    if not isinstance(successes, int) or not isinstance(attempts, int):
        raise ValueError("HOLD_NONINTEGER_COUNTS")
    if attempts <= 0 or not 0 <= successes <= attempts:
        raise ValueError("HOLD_COUNTS")
    p = successes / attempts
    den = 1 + z*z / attempts
    ctr = (p + z*z/(2*attempts)) / den
    half = z*((p*(1-p)/attempts + z*z/(4*attempts*attempts))**0.5)/den
    return (ctr-half, ctr+half)

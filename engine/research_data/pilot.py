"""Small manifest contracts for the M12-B0 feasibility run."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator

from engine.calibration_models import CalibrationDataQuality
from engine.research_data.contracts import ResearchDataFailureReason
from engine.research_data.sampling import PilotSamplePlan
from engine.tracking_models import FrozenDomainModel, ResolutionState


class PilotVerdict(str, Enum):
    PASS = "pass"
    PASS_WITH_GAPS = "pass_with_gaps"
    FAIL = "fail"


class PilotAnchorResult(FrozenDomainModel):
    anchor_year: int
    discovery_records_returned: int = Field(ge=0)
    validated_security_candidates: int = Field(ge=0)
    sampled: int = Field(ge=0)
    case1_eligible: int = Field(ge=0)
    case1_resolved: int = Field(ge=0)
    case2_eligible: int = Field(ge=0)
    case2_resolved: int = Field(ge=0)
    performance_resolved: int = Field(ge=0)
    quality: CalibrationDataQuality
    unresolved_reasons: tuple[ResearchDataFailureReason, ...] = ()
    note: str

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.sampled > self.validated_security_candidates:
            raise ValueError("sampled count cannot exceed validated security candidates")
        if self.case1_resolved > self.case1_eligible or self.case2_resolved > self.case2_eligible:
            raise ValueError("resolved Case count cannot exceed eligible count")
        if self.case1_eligible > self.sampled or self.case2_eligible > self.sampled:
            raise ValueError("eligible Case count cannot exceed sampled count")
        if self.performance_resolved > self.case1_resolved + self.case2_resolved:
            raise ValueError("performance count cannot exceed resolved Case analyses")
        if self.quality == CalibrationDataQuality.COMPLETE and self.unresolved_reasons:
            raise ValueError("complete anchor cannot contain unresolved reasons")
        if self.quality != CalibrationDataQuality.COMPLETE and not self.unresolved_reasons:
            raise ValueError("incomplete anchor requires unresolved reasons")
        return self


class StressSetResult(FrozenDomainModel):
    sample_id: str
    event_type: str
    analysis_state: ResolutionState
    performance_state: ResolutionState
    calibration_cohort: bool = False
    unresolved_reasons: tuple[ResearchDataFailureReason, ...] = ()
    note: str

    @model_validator(mode="after")
    def keep_outcome_aware_samples_separate(self) -> Self:
        if self.calibration_cohort:
            raise ValueError("outcome-aware stress samples cannot enter calibration cohort")
        if (
            self.analysis_state == ResolutionState.UNRESOLVED
            or self.performance_state == ResolutionState.UNRESOLVED
        ) and not self.unresolved_reasons:
            raise ValueError("unresolved stress result requires a reason")
        return self


class M12B0PilotManifest(FrozenDomainModel):
    schema_version: str
    executed_at: datetime
    run_mode: str
    sample_plan: PilotSamplePlan
    anchors: tuple[PilotAnchorResult, ...]
    stress_set: tuple[StressSetResult, ...]
    verdict: PilotVerdict
    cohort_records_produced: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        if self.executed_at.tzinfo is None or self.executed_at.utcoffset() is None:
            raise ValueError("executed_at must be timezone-aware")
        years = [item.anchor_year for item in self.anchors]
        if years != [2018, 2021, 2022]:
            raise ValueError("M12-B0 anchors must be ordered as 2018, 2021, 2022")
        if self.run_mode != "pilot":
            raise ValueError("M12-B0 manifest must use pilot run mode")
        resolved = sum(item.case1_resolved + item.case2_resolved for item in self.anchors)
        if self.cohort_records_produced > resolved:
            raise ValueError("cohort records cannot exceed resolved Case analyses")
        return self


def load_pilot_manifest(path: str | Path) -> M12B0PilotManifest:
    return M12B0PilotManifest.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

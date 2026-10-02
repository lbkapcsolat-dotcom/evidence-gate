# Alternate Freshwater Explicit Interval Source Discovery V1

This gate searches for one official-primary replacement freshwater source after
the Environment Agency flow-mean source family was closed fail-closed.

Pinned predecessor receipt SHA256:

`ffb19d37f292fcbeb207c17c261f15dfaa9ab8b484571e81d31f591a69bf93d3`

## Selected replacement source

Provider: Australian Bureau of Meteorology  
Surface: Water Data Online SOS2 / WaterML2  
Station: `410713`, Paddys at Riverlea  
Procedure: `Pat4_C_B_1_DailyMean`, `DMQaQc.Merged.DailyMean.24HR`  
Observed property: `Water Course Discharge`

Official documentation:
https://www.bom.gov.au/waterdata/wiski-web-public/faq.htm

The Bureau states that mean values are time-weighted means over an interval from
00:00:00 to 00:00:00 the following day and that the mean value is recorded at
the start of the interval.

The live SOS2 GetObservation response independently carries an
`om:phenomenonTime/gml:TimePeriod` with explicit boundaries:

- begin: `2026-09-30T00:00:00.000+10:00`
- end: `2026-10-01T00:00:00.000+10:00`
- duration: 86,400 seconds

The returned WaterML2 time-value pair is:

- value time: `2026-09-30T00:00:00.000+10:00`
- value: `0.378`
- unit code: `cumec`

The Bureau's official water terminology defines cumecs as cubic metres per
second, so this is a freshwater discharge-rate quantity.

Frozen raw response:

`sources/bom/410713_discharge_daily_mean_2026-09-30.xml`

Raw UTF-8 bytes: `2735`

Raw SHA256:

`1fe8f1416b69377160ed6c9fced011785a46e7cb52eac46ce783a424c3e7ee14`

## Interpolation / aggregation scope

No interpolation or imputation is performed by Equilibrium. The source-native
daily time-weighted mean is consumed exactly as published. The WaterML2 response
also contains source metadata `ConstSucc` / "Constant in succeeding interval";
that metadata is preserved rather than executed as a new Equilibrium
transformation.

No interval boundary is inferred: both begin and end are present directly in the
source response.

## Verdict

`PASS_BOUNDED_ALTERNATE_FRESHWATER_EXPLICIT_INTERVAL_SOURCE_DISCOVERY`

This PASS is source-discovery only. It does not prove three-source temporal
alignment, composition, runtime admission, production use, EQ scoring, UI,
pointer promotion, global bind, or merge.

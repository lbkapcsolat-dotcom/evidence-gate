from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass, replace
import json, math
import numpy as np
import xarray as xr

ALLOWED_UNCERTAINTY={"EXACT","INTERVAL","ENSEMBLE","MOMENT","EMPIRICAL"}
REQUIRED_COORDS={"variable","lat","lon"}

@dataclass(frozen=True)
class Evidence:
    source_id:str="ESSDeterministicLocalDataSource"
    source_version:str="1.0.0"
    model_id:str="earth2studio.models.px.Persistence"
    model_version:str="earth2studio@1a6e3669db0b04c1b42253cf0e631ed1ee8817ea"
    time_start:str="2024-01-01T00:00:00"
    time_end:str="2024-01-01T06:00:00"
    lead_hours:float=6.0
    variables:tuple[str,...]=("t2m",)
    units:tuple[str,...]=("K",)
    coord_keys:tuple[str,...]=("time","lead_time","variable","lat","lon")
    operator_id:str="earth2studio.run.deterministic"
    operator_version:str="earth2studio@1a6e3669db0b04c1b42253cf0e631ed1ee8817ea"
    uncertainty_kind:str="EXACT"
    domain_invariants_ok:bool=True
    provenance_digest:str="a"*64

def _hex64(x): return len(x)==64 and all(c in "0123456789abcdef" for c in x.lower())
def observe(e):
    b1=bool(e.source_id and e.source_version and e.model_id and e.model_version and e.operator_id and e.operator_version and _hex64(e.provenance_digest))
    try:
        t0=np.datetime64(e.time_start); t1=np.datetime64(e.time_end)
        b2=bool(t0<t1 and math.isfinite(float(e.lead_hours)) and float(e.lead_hours)>=0)
    except Exception: b2=False
    b3=bool(e.variables and len(e.variables)==len(e.units) and all(e.variables) and all(e.units) and REQUIRED_COORDS.issubset(set(e.coord_keys)))
    bad={"","NONE","UNKNOWN"}
    b4=bool(e.model_id not in bad and e.model_version not in bad and e.operator_id not in bad and e.operator_version not in bad)
    b5=e.uncertainty_kind in ALLOWED_UNCERTAINTY
    b6=e.domain_invariants_ok is True
    bits=(b1,b2,b3,b4,b5,b6)
    state=sum((1 if b else 0)<<(5-i) for i,b in enumerate(bits))
    return {"bits":"".join("1" if b else "0" for b in bits),"state":state,"verdict":"PASS_BOUNDED" if state==63 else "HOLD"}

def fixtures():
    n=Evidence()
    return [
      ("NOMINAL",n,"PASS_BOUNDED"),
      ("MISSING_PROVENANCE",replace(n,provenance_digest=""),"HOLD"),
      ("UNKNOWN_SOURCE_VERSION",replace(n,source_version=""),"HOLD"),
      ("REVERSED_TIME",replace(n,time_end="2023-12-31T18:00:00"),"HOLD"),
      ("NAN_LEAD",replace(n,lead_hours=float("nan")),"HOLD"),
      ("NEGATIVE_LEAD",replace(n,lead_hours=-6.0),"HOLD"),
      ("MISSING_UNIT",replace(n,units=("",)),"HOLD"),
      ("UNIT_CARDINALITY_MISMATCH",replace(n,units=("K","m/s")),"HOLD"),
      ("MISSING_COORD_AXIS",replace(n,coord_keys=("time","lead_time","variable","lat")),"HOLD"),
      ("ARBITRARY_OPERATOR",replace(n,operator_id="UNKNOWN"),"HOLD"),
      ("MISSING_MODEL_VERSION",replace(n,model_version=""),"HOLD"),
      ("UNKNOWN_UNCERTAINTY",replace(n,uncertainty_kind="UNKNOWN"),"HOLD"),
      ("DOMAIN_INVARIANT_FAIL",replace(n,domain_invariants_ok=False),"HOLD"),
      ("UNKNOWN_MODEL_ID",replace(n,model_id="UNKNOWN"),"HOLD"),
      ("BAD_PROVENANCE_LENGTH",replace(n,provenance_digest="a"*63),"HOLD"),
    ]

def evidence_json(e): return json.dumps(e.__dict__,sort_keys=True,separators=(",",":"))

class ESSDeterministicLocalDataSource:
    def __init__(self):
        self.lat=np.array([1.0,0.0],dtype=np.float32)
        self.lon=np.array([0.0,1.0],dtype=np.float32)
    def __call__(self,time,variable):
        time=np.atleast_1d(np.asarray(time,dtype="datetime64[ns]"))
        variable=np.atleast_1d(np.asarray(variable,dtype=str))
        data=np.arange(time.size*variable.size*self.lat.size*self.lon.size,dtype=np.float32).reshape(time.size,variable.size,self.lat.size,self.lon.size)
        return xr.DataArray(data,dims=("time","variable","lat","lon"),coords={"time":time,"variable":variable,"lat":self.lat,"lon":self.lon})

def run_real_earth2studio():
    import earth2studio, torch
    from earth2studio.models.px import Persistence
    from earth2studio.io import ZarrBackend
    import earth2studio.run as run
    domain=OrderedDict([("lat",np.array([1.0,0.0],dtype=np.float32)),("lon",np.array([0.0,1.0],dtype=np.float32))])
    model=Persistence(["t2m"],domain)
    data=ESSDeterministicLocalDataSource()
    sample=data(np.array([np.datetime64("2024-01-01T00:00:00")]),np.array(["t2m"]))
    assert sample.dims==("time","variable","lat","lon")
    io=ZarrBackend()
    result=run.deterministic(["2024-01-01T00:00:00"],2,model,data,io,device=torch.device("cpu"),verbose=False)
    assert result is io
    return {"earth2studio_version":getattr(earth2studio,"__version__","UNKNOWN"),"datasource_dims":list(sample.dims),"workflow":"PASS","model":"Persistence","device":"cpu"}

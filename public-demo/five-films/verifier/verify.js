#!/usr/bin/env node
/* Independent reference verifier for offline synthetic demonstration files only.
 * It is not a signature verifier, cryptographic provenance service, or enforcement tool.
 */
'use strict';
const fs = require('fs');
const crypto = require('crypto');
const domain = Buffer.from('PUBLIC-PROOFGATE-SYNTHETIC-V1\0', 'ascii');
const keysInput = ['schema','case_id','authority_revision','expected_authority_revision','operation_kind','granted_scopes','requested_scope','authority_attested','policy_attested','evidence_attested','q6_required','q6_observed','synthetic_only'];
const keysPassport = ['schema','frozen_inputs','decision_core','decision_core_sha256','event_origin_attested','external_integrity_pin_verified','production_enforcement'];
const stable = obj => {
  if (Array.isArray(obj)) return '['+obj.map(stable).join(',')+']';
  if (obj !== null && typeof obj === 'object') return '{'+Object.keys(obj).sort().map(k=>JSON.stringify(k)+':'+stable(obj[k])).join(',')+'}';
  return JSON.stringify(obj);
};
const hash = x => crypto.createHash('sha256').update(domain).update(Buffer.from(stable(x),'ascii')).digest('hex');
const exactKeys = (v,keys) => v && !Array.isArray(v) && typeof v==='object' && Object.keys(v).length===keys.length && keys.every(k=>Object.hasOwn(v,k));
const bits = a => Array.isArray(a) && a.length===6 && a.every(x=>Number.isInteger(x)&&(x===0||x===1));
function decide(d){
 if(!exactKeys(d,keysInput))return ['HOLD','INPUT_SCHEMA_MISMATCH'];
 if(d.schema!=='PUBLIC_SYNTHETIC_INPUT_V1'||d.synthetic_only!==true)return['HOLD','NON_SYNTHETIC_INPUT_REFUSED'];
 if(['authority_attested','policy_attested','evidence_attested'].some(k=>typeof d[k]!=='boolean'))return['HOLD','INVALID_ATTESTATION_FIELDS'];
 if(['authority_revision','expected_authority_revision'].some(k=>!Number.isSafeInteger(d[k])||d[k]<0))return['HOLD','INVALID_REVISION'];
 if(!['READ_ONLY','WRITE_SENSITIVE'].includes(d.operation_kind))return['HOLD','INVALID_OPERATION'];
 if(!Array.isArray(d.granted_scopes)||!d.granted_scopes.every(x=>typeof x==='string'))return['HOLD','INVALID_SCOPES'];
 if(typeof d.requested_scope!=='string')return['HOLD','INVALID_REQUESTED_SCOPE'];
 if(!bits(d.q6_required)||!bits(d.q6_observed))return['HOLD','INVALID_Q6'];
 if(!d.granted_scopes.includes(d.requested_scope))return['DENY','OUT_OF_SCOPE'];
 if(d.authority_revision!==d.expected_authority_revision)return['HOLD','STALE_AUTHORITY'];
 if(!d.authority_attested)return['HOLD','AUTHORITY_UNVERIFIED'];
 if(!d.evidence_attested)return['HOLD','EVIDENCE_UNVERIFIED'];
 if(!d.policy_attested)return['HOLD','POLICY_UNVERIFIED'];
 if(d.operation_kind==='WRITE_SENSITIVE'&&d.q6_required[5]!==1)return['DENY','REQUIRED_HUMAN_GUARD_DISABLED'];
 if(d.q6_observed.some((v,i)=>v<d.q6_required[i]))return['HOLD','Q6_DOMINANCE_FAILED'];
 return['PASS_BOUNDED','DECLARED_GUARDS_CONSISTENT'];
}
function verify(p){
 if(!exactKeys(p,keysPassport))return{result:'DENY',reason:'PASSPORT_SCHEMA_MISMATCH'};
 if(p.schema!=='PUBLIC_SYNTHETIC_PROOF_PASSPORT_V1'||
    ['event_origin_attested','external_integrity_pin_verified','production_enforcement'].some(k=>p[k]!==false))return{result:'DENY',reason:'OVERCLAIM_OR_SCHEMA'};
 const [verdict,reason]=decide(p.frozen_inputs);
 const core={schema:'PUBLIC_DECISION_CORE_V1',frozen_input_sha256:hash(p.frozen_inputs),verdict,reason,execution_eligible:false};
 const expected={schema:'PUBLIC_SYNTHETIC_PROOF_PASSPORT_V1',frozen_inputs:p.frozen_inputs,decision_core:core,decision_core_sha256:hash(core),event_origin_attested:false,external_integrity_pin_verified:false,production_enforcement:false};
 if(stable(p)!==stable(expected))return{result:'DENY',reason:'DECISION_OR_DIGEST_MISMATCH'};
 return{result:'REPLAY_MATCH',reason:'LOCAL_SYNTHETIC_ONLY',verdict,core_sha256:hash(core)};
}
if(require.main===module){
 if(process.argv.length!==3){console.error('Usage: node verifier/verify.js passports/01-fbi-jobs-data-release.json');process.exit(2)}
 try{let p=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));let r=verify(p);console.log(JSON.stringify(r,null,2));process.exit(r.result==='REPLAY_MATCH'?0:1)}catch(e){console.error('Malformed JSON or file: '+e.message);process.exit(2)}
}
module.exports={verify,decide,stable,hash};

#!/usr/bin/env node
/* Synthetic sample checker. Does not authenticate events or enforce policies. */
const fs=require('fs'),crypto=require('crypto');
const d=Buffer.concat([Buffer.from('PUBLIC-PROOFGATE-SYNTHETIC-V1','ascii'),Buffer.from([0])]);
const stable=v=>Array.isArray(v)?'['+v.map(stable).join(',')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}':JSON.stringify(v);
const hash=v=>crypto.createHash('sha256').update(d).update(stable(v),'ascii').digest('hex');
let p;
try{p=JSON.parse(fs.readFileSync(process.argv[2]||__dirname+'/passports/01-fbi-jobs-data-release.json','utf8'))}catch(e){console.error('Invalid JSON:',e.message);process.exit(2)}
const a=p.frozen_inputs||{};
const fail=(why)=>{console.error('DENY:',why);process.exit(1)};
if(p.schema!=='PUBLIC_SYNTHETIC_PROOF_PASSPORT_V1'||p.event_origin_attested!==false||p.production_enforcement!==false||p.external_integrity_pin_verified!==false)fail('INVALID_CLAIM');
if(a.schema!=='PUBLIC_SYNTHETIC_INPUT_V1'||a.synthetic_only!==true||a.case_id!=='fbi-jobs-data-release')fail('WRONG_SAMPLE');
const scopes=(a.granted_scopes||[]);
let verdict='PASS_BOUNDED',reason='DECLARED_GUARDS_CONSISTENT';
if(!scopes.includes(a.requested_scope)){verdict='DENY';reason='OUT_OF_SCOPE'}
else if(a.authority_revision!==a.expected_authority_revision){verdict='HOLD';reason='STALE_AUTHORITY'}
else if(a.authority_attested!==true){verdict='HOLD';reason='AUTHORITY_UNVERIFIED'}
else if(a.evidence_attested!==true){verdict='HOLD';reason='EVIDENCE_UNVERIFIED'}
else if(a.policy_attested!==true){verdict='HOLD';reason='POLICY_UNVERIFIED'}
else if(!Array.isArray(a.q6_required)||!Array.isArray(a.q6_observed)||a.q6_observed.length!==6||a.q6_required.length!==6){verdict='HOLD';reason='INVALID_Q6'}
else if(a.q6_observed.some((b,i)=>b<a.q6_required[i])){verdict='HOLD';reason='Q6_DOMINANCE_FAILED'}
const core={schema:'PUBLIC_DECISION_CORE_V1',frozen_input_sha256:hash(a),verdict,reason,execution_eligible:false};
if(stable(core)!==stable(p.decision_core)||hash(core)!==p.decision_core_sha256)fail('REPLAY_MISMATCH');
console.log(JSON.stringify({result:'REPLAY_MATCH',verdict,reason,core_sha256:hash(core),real_world_blocking:false},null,2));

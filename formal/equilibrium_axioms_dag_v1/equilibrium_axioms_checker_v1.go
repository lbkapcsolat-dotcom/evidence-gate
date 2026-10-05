package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"sort"
)

type Lease struct {
	Q               int    `json:"q"`
	GraphVersion    int    `json:"graph_version"`
	RegistryVersion int    `json:"registry_version"`
	EvidenceEpoch   int    `json:"evidence_epoch"`
	ProofEpoch      int    `json:"proof_epoch"`
	EvidenceDigest  string `json:"evidence_digest"`
	ContentDigest   string `json:"content_digest"`
}
type Fixture struct {
	ID                        string `json:"id"`
	Candidates                []int  `json:"candidates"`
	Quality                   string `json:"quality"`
	ObservationFresh          bool   `json:"observation_fresh"`
	ProvenanceComplete        bool   `json:"provenance_complete"`
	ProvenanceVerified        bool   `json:"provenance_verified"`
	EffectiveDomains          int    `json:"effective_domains"`
	QuorumRequired            int    `json:"quorum_required"`
	QuorumMode                string `json:"quorum_mode"`
	IdentityState             string `json:"identity_state"`
	IdentityCurrentEpoch      bool   `json:"identity_current_epoch"`
	EvidenceChainValid        bool   `json:"evidence_chain_valid"`
	LocalBound                bool   `json:"local_bound"`
	OverlapDefects            int    `json:"overlap_defects"`
	GlueComplete              bool   `json:"glue_complete"`
	GraphVersion              int    `json:"graph_version"`
	RegistryVersion           int    `json:"registry_version"`
	EvidenceEpoch             int    `json:"evidence_epoch"`
	ProofEpoch                int    `json:"proof_epoch"`
	EvidenceDigest            string `json:"evidence_digest"`
	ContentDigest             string `json:"content_digest"`
	Lease                     *Lease `json:"lease"`
	BoundedProof              bool   `json:"bounded_proof"`
	RuntimeRequested          bool   `json:"runtime_requested"`
	ProductionRequested       bool   `json:"production_requested"`
	PointerPromotionRequested bool   `json:"pointer_promotion_requested"`
	GlobalBindRequested       bool   `json:"global_bind_requested"`
}

func exactQ(s Fixture) (int, bool) {
	if s.Quality == "EXACT" && len(s.Candidates) == 1 {
		return s.Candidates[0], true
	}
	return 0, false
}
func leaseMatches(s Fixture) bool {
	if s.Lease == nil {
		return false
	}
	q, ok := exactQ(s)
	if !ok {
		return false
	}
	l := s.Lease
	return l.Q == q && l.GraphVersion == s.GraphVersion && l.RegistryVersion == s.RegistryVersion &&
		l.EvidenceEpoch == s.EvidenceEpoch && l.ProofEpoch == s.ProofEpoch &&
		l.EvidenceDigest == s.EvidenceDigest && l.ContentDigest == s.ContentDigest
}
func checks(s Fixture) map[string]bool {
	qtyped := true
	for _, x := range s.Candidates {
		if x < 0 || x >= 64 {
			qtyped = false
		}
	}
	if s.Quality == "MISSING" {
		qtyped = qtyped && len(s.Candidates) == 0
	} else {
		qtyped = qtyped && len(s.Candidates) > 0
	}
	ax02 := (s.Quality != "EXACT" || len(s.Candidates) == 1) && (s.Quality != "MISSING" || len(s.Candidates) == 0)
	ax03 := s.ObservationFresh || (!s.LocalBound && s.Lease == nil && s.QuorumMode != "EXACT")
	ax05 := s.QuorumMode != "EXACT" || (s.ProvenanceComplete && s.ProvenanceVerified)
	ax06 := s.QuorumMode != "EXACT" || s.EffectiveDomains >= s.QuorumRequired
	ax07 := s.QuorumMode != "EXACT" || (s.IdentityState == "ACTIVE" && s.IdentityCurrentEpoch && s.EvidenceChainValid)
	ax08 := true
	if s.QuorumMode == "ROBUST" {
		ax08 = s.Quality != "EXACT" && !s.LocalBound && s.Lease == nil
	}
	if s.QuorumMode == "EXACT" {
		_, ok := exactQ(s)
		ax08 = ax08 && ok
	}
	_, exact := exactQ(s)
	ax09 := !s.LocalBound || (exact && s.ObservationFresh && s.OverlapDefects == 0 && s.GlueComplete)
	ax10 := s.Lease == nil || leaseMatches(s)
	ax11 := s.Lease == nil || (s.Lease.ProofEpoch == s.ProofEpoch && s.Lease.GraphVersion == s.GraphVersion && s.Lease.RegistryVersion == s.RegistryVersion)
	ax12 := true
	if s.IdentityState == "REVOKED" {
		ax12 = s.QuorumMode != "EXACT" && s.Lease == nil && !s.LocalBound
	}
	ax14 := !s.BoundedProof || !(s.RuntimeRequested || s.ProductionRequested || s.PointerPromotionRequested || s.GlobalBindRequested)
	ax16 := true
	if s.LocalBound || s.Lease != nil {
		ax16 = exact && s.ObservationFresh && s.ProvenanceComplete && s.ProvenanceVerified &&
			s.EffectiveDomains >= s.QuorumRequired && s.IdentityState == "ACTIVE" &&
			s.IdentityCurrentEpoch && s.EvidenceChainValid && s.OverlapDefects == 0 && s.GlueComplete
	}
	return map[string]bool{
		"AX01": qtyped, "AX02": ax02, "AX03": ax03, "AX05": ax05, "AX06": ax06, "AX07": ax07,
		"AX08": ax08, "AX09": ax09, "AX10": ax10, "AX11": ax11, "AX12": ax12, "AX14": ax14, "AX16": ax16,
	}
}
func classification(s Fixture) map[string]interface{} {
	ch := checks(s)
	failed := []string{}
	for k, v := range ch {
		if !v {
			failed = append(failed, k)
		}
	}
	sort.Strings(failed)
	if len(failed) > 0 {
		return map[string]interface{}{"status": "HOLD", "failed_axioms": failed}
	}
	if s.QuorumMode == "EXACT" {
		q, _ := exactQ(s)
		status := "PASS_EXACT_BOUND"
		if s.LocalBound && s.Lease != nil {
			status = "PASS_EXACT_GLOBAL"
		}
		return map[string]interface{}{"status": status, "q": q, "failed_axioms": []string{}}
	}
	if s.QuorumMode == "ROBUST" {
		env := append([]int(nil), s.Candidates...)
		sort.Ints(env)
		return map[string]interface{}{"status": "PASS_ROBUST_ONLY", "envelope": env, "failed_axioms": []string{}}
	}
	return map[string]interface{}{"status": "HOLD_NO_QUORUM", "failed_axioms": []string{}}
}
func shaBody(v interface{}) string {
	b, _ := json.Marshal(v)
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}
func result(s Fixture) map[string]interface{} {
	body := map[string]interface{}{
		"fixture_id":     s.ID,
		"classification": classification(s),
		"axiom_checks":   checks(s),
		"quality":        s.Quality,
		"quorum_mode":    s.QuorumMode,
		"versions":       map[string]interface{}{"graph": s.GraphVersion, "registry": s.RegistryVersion, "evidence_epoch": s.EvidenceEpoch, "proof_epoch": s.ProofEpoch},
	}
	body["receipt_digest"] = shaBody(body)
	return body
}

func bools(n int, fn func([]bool)) {
	total := 1 << n
	for mask := 0; mask < total; mask++ {
		b := make([]bool, n)
		for i := 0; i < n; i++ {
			b[i] = ((mask >> i) & 1) == 1
		}
		fn(b)
	}
}
func derivedObligations() map[string]interface{} {
	c9, c11, c12 := 0, 0, 0
	bools(11, func(b []bool) {
		local, lease, exact, fresh, overlap, glue, prov, indep, active, epoch, chain := b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10]
		ax16 := !(local || lease) || (exact && fresh && prov && indep && active && epoch && chain && overlap && glue)
		ax09 := !local || (exact && fresh && overlap && glue)
		if ax16 && !ax09 {
			c9++
		}
	})
	bools(8, func(b []bool) {
		lease, qmatch, graph, registry, evepoch, proof, evdig, content := b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7]
		ax10 := !lease || (qmatch && graph && registry && evepoch && proof && evdig && content)
		ax11 := !lease || (proof && graph && registry)
		if ax10 && !ax11 {
			c11++
		}
	})
	bools(13, func(b []bool) {
		exactqm, active, revoked, epoch, chain, local, lease, exact, fresh, prov, indep, overlap, glue := b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10], b[11], b[12]
		if active && revoked {
			return
		}
		ax07 := !exactqm || (active && epoch && chain)
		ax16 := !(local || lease) || (exact && fresh && prov && indep && active && epoch && chain && overlap && glue)
		ax12 := !revoked || (!exactqm && !lease && !local)
		if ax07 && ax16 && !ax12 {
			c12++
		}
	})
	return map[string]interface{}{
		"PO_AX09": map[string]interface{}{"passed": c9 == 0, "counterexample_count": c9},
		"PO_AX11": map[string]interface{}{"passed": c11 == 0, "counterexample_count": c11},
		"PO_AX12": map[string]interface{}{"passed": c12 == 0, "counterexample_count": c12},
	}
}
func isHold(r map[string]interface{}) bool {
	s := r["classification"].(map[string]interface{})["status"].(string)
	return s == "HOLD" || s == "HOLD_NO_QUORUM"
}
func corpusObligations(fixtures []Fixture, results []map[string]interface{}) map[string]interface{} {
	robust, t2, t3, t4, t5, t6, t7, t8 := 0, 0, 0, 0, 0, 0, 0, 0
	ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8 := true, true, true, true, true, true, true, true
	for i, f := range fixtures {
		r := results[i]
		status := r["classification"].(map[string]interface{})["status"].(string)
		if f.QuorumMode == "ROBUST" {
			robust++
			if status == "PASS_EXACT_BOUND" || status == "PASS_EXACT_GLOBAL" {
				ok1 = false
			}
		}
		if f.QuorumMode == "EXACT" && (!f.ProvenanceComplete || !f.ProvenanceVerified || f.EffectiveDomains < f.QuorumRequired) {
			t2++
			if !isHold(r) {
				ok2 = false
			}
		}
		if f.Lease != nil && (f.Lease.GraphVersion != f.GraphVersion || f.Lease.RegistryVersion != f.RegistryVersion || f.Lease.EvidenceEpoch != f.EvidenceEpoch || f.Lease.ProofEpoch != f.ProofEpoch || f.Lease.EvidenceDigest != f.EvidenceDigest || f.Lease.ContentDigest != f.ContentDigest) {
			t3++
			if !isHold(r) {
				ok3 = false
			}
		}
		if f.LocalBound && (f.OverlapDefects != 0 || !f.GlueComplete) {
			t4++
			if !isHold(r) {
				ok4 = false
			}
		}
		if f.IdentityState == "REVOKED" {
			t5++
			if !isHold(r) {
				ok5 = false
			}
		}
		if f.BoundedProof && (f.RuntimeRequested || f.ProductionRequested || f.PointerPromotionRequested || f.GlobalBindRequested) {
			t6++
			if !isHold(r) {
				ok6 = false
			}
		}
		hasFail := false
		for _, v := range r["axiom_checks"].(map[string]bool) {
			if !v {
				hasFail = true
			}
		}
		if hasFail {
			t7++
			if !isHold(r) {
				ok7 = false
			}
		}
		if (f.LocalBound || f.Lease != nil) && !r["axiom_checks"].(map[string]bool)["AX16"] {
			t8++
			if !isHold(r) {
				ok8 = false
			}
		}
	}
	return map[string]interface{}{
		"PO_T1": map[string]interface{}{"passed": robust > 0 && ok1, "witness_count": robust},
		"PO_T2": map[string]interface{}{"passed": t2 > 0 && ok2, "witness_count": t2},
		"PO_T3": map[string]interface{}{"passed": t3 > 0 && ok3, "witness_count": t3},
		"PO_T4": map[string]interface{}{"passed": t4 > 0 && ok4, "witness_count": t4},
		"PO_T5": map[string]interface{}{"passed": t5 > 0 && ok5, "witness_count": t5},
		"PO_T6": map[string]interface{}{"passed": t6 > 0 && ok6, "witness_count": t6},
		"PO_T7": map[string]interface{}{"passed": t7 > 0 && ok7, "witness_count": t7},
		"PO_T8": map[string]interface{}{"passed": t8 > 0 && ok8, "witness_count": t8},
	}
}
func obligations(fixtures []Fixture, results []map[string]interface{}) map[string]interface{} {
	out := derivedObligations()
	for k, v := range corpusObligations(fixtures, results) {
		out[k] = v
	}
	return out
}
func main() {
	if len(os.Args) < 2 {
		panic("usage: checker fixtures.json [obligations]")
	}
	b, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	var fixtures []Fixture
	if err = json.Unmarshal(b, &fixtures); err != nil {
		panic(err)
	}
	out := make([]map[string]interface{}, 0, len(fixtures))
	for _, f := range fixtures {
		out = append(out, result(f))
	}
	var enc []byte
	if len(os.Args) == 3 && os.Args[2] == "obligations" {
		enc, _ = json.Marshal(obligations(fixtures, out))
	} else {
		enc, _ = json.Marshal(out)
	}
	fmt.Print(string(enc))
}

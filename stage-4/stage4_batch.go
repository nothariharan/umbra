package main

import (
	"encoding/json"
	"net/http"
	"time"
)

type batchCorrectionItem struct {
	paymentID       string
	expectedRev     int
	amount          int64
	effectiveAt     string
	reason          string
	effectiveTime   time.Time
}

func (sv *Server) handleCorrectionBatch(w http.ResponseWriter, r *http.Request) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	raw, ok := readBody(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid body")
		return
	}
	sv.runIdempotent(w, r, u, raw, func(w http.ResponseWriter, raw []byte) (int, []byte, bool, bool) {
		sv.store.mu.Lock()
		defer sv.store.mu.Unlock()
		if _, op := sv.store.SettlementOperators[u.ID]; !op {
			b, f := errResp(http.StatusForbidden, "forbidden", "not operator")
			return http.StatusForbidden, b, f, true
		}

		var body map[string]json.RawMessage
		if err := json.Unmarshal(raw, &body); err != nil {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid json")
			return http.StatusBadRequest, b, f, true
		}
		rawItems, ok := body["corrections"]
		if !ok {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid corrections")
			return http.StatusUnprocessableEntity, b, f, true
		}
		var itemsRaw []map[string]json.RawMessage
		if err := json.Unmarshal(rawItems, &itemsRaw); err != nil {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid corrections")
			return http.StatusUnprocessableEntity, b, f, true
		}
		if len(itemsRaw) < 1 || len(itemsRaw) > 32 {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid corrections")
			return http.StatusUnprocessableEntity, b, f, true
		}

		seenPID := map[string]struct{}{}
		var items []batchCorrectionItem
		for _, it := range itemsRaw {
			pid, ek := stringField(it, "payment_id")
			if ek == errMalformed {
				b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid payment_id")
				return http.StatusBadRequest, b, f, true
			}
			if pid == "" {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid payment_id")
				return http.StatusUnprocessableEntity, b, f, true
			}
			if _, dup := seenPID[pid]; dup {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "duplicate payment_id")
				return http.StatusUnprocessableEntity, b, f, true
			}
			seenPID[pid] = struct{}{}

			expRev, expOk, expEk := parseExpectedRevision(it["expected_revision"])
			if expEk == errMalformed {
				b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid expected_revision")
				return http.StatusBadRequest, b, f, true
			}
			if !expOk {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid expected_revision")
				return http.StatusUnprocessableEntity, b, f, true
			}
			amount, amtOk, amtEk := parseNonNegativeAmount(it["amount"])
			if amtEk == errMalformed {
				b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid amount")
				return http.StatusBadRequest, b, f, true
			}
			if !amtOk {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid amount")
				return http.StatusUnprocessableEntity, b, f, true
			}
			effectiveAt, effEk := stringField(it, "effective_at")
			if effEk == errMalformed {
				b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid effective_at")
				return http.StatusBadRequest, b, f, true
			}
			if effEk == errValidation || effectiveAt == "" {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid effective_at")
				return http.StatusUnprocessableEntity, b, f, true
			}
			effT, okT := parseTime(effectiveAt)
			if !okT {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid effective_at")
				return http.StatusUnprocessableEntity, b, f, true
			}
			if effT.After(now()) {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid effective_at")
				return http.StatusUnprocessableEntity, b, f, true
			}
			reason, rEk := stringField(it, "reason")
			if rEk == errMalformed {
				b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid reason")
				return http.StatusBadRequest, b, f, true
			}
			if reason == "" || len(reason) > 200 {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid reason")
				return http.StatusUnprocessableEntity, b, f, true
			}

			if sv.store.findPaymentIndex(pid) < 0 {
				b, f := errResp(http.StatusNotFound, "not_found", "payment not found")
				return http.StatusNotFound, b, f, true
			}
			p := sv.store.Payments[sv.store.findPaymentIndex(pid)]
			if p.RefundOf != nil || p.AuthorizationID != nil {
				b, f := errResp(http.StatusUnprocessableEntity, "linked_payment_immutable", "linked payment immutable")
				return http.StatusUnprocessableEntity, b, f, true
			}
			cur, okRev := sv.store.latestRevisionLocked(pid)
			if !okRev || cur.Revision != expRev {
				b, f := errResp(http.StatusConflict, "stale_revision", "stale revision")
				return http.StatusConflict, b, f, true
			}
			if amount < sv.store.totalRefundedLocked(pid) {
				b, f := errResp(http.StatusUnprocessableEntity, "refund_exceeds_payment", "refund exceeds payment")
				return http.StatusUnprocessableEntity, b, f, true
			}

			items = append(items, batchCorrectionItem{
				paymentID: pid, expectedRev: expRev, amount: amount,
				effectiveAt: effectiveAt, reason: reason, effectiveTime: effT,
			})
		}

		batchSet := map[string]map[string]struct{}{}
		for _, it := range items {
			idx := sv.store.findPaymentIndex(it.paymentID)
			p := sv.store.Payments[idx]
			if p.SettlementID == nil {
				continue
			}
			sid := *p.SettlementID
			if batchSet[sid] == nil {
				batchSet[sid] = map[string]struct{}{}
			}
			batchSet[sid][it.paymentID] = struct{}{}
		}
		for sid, inBatch := range batchSet {
			members := sv.store.settlementMembersLocked(sid)
			for _, mid := range members {
				if _, ok := inBatch[mid]; !ok {
					b, f := errResp(http.StatusUnprocessableEntity, "incomplete_settlement", "incomplete settlement")
					return http.StatusUnprocessableEntity, b, f, true
				}
			}
		}
		for sid, inBatch := range batchSet {
			var ref time.Time
			first := true
			for pid := range inBatch {
				for _, it := range items {
					if it.paymentID == pid {
						if first {
							ref = it.effectiveTime
							first = false
						} else if !it.effectiveTime.Equal(ref) {
							b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "settlement effective mismatch")
							return http.StatusUnprocessableEntity, b, f, true
						}
						break
					}
				}
			}
			_ = sid
		}

		netDelta := map[string]int64{}
		for _, it := range items {
			idx := sv.store.findPaymentIndex(it.paymentID)
			p := sv.store.Payments[idx]
			cur, _ := sv.store.latestRevisionLocked(it.paymentID)
			delta := it.amount - cur.Amount
			netDelta[p.FromUserID] -= delta
			netDelta[p.ToUserID] += delta
		}
		for uid, delta := range netDelta {
			if delta >= 0 {
				continue
			}
			if sv.store.availableForUserLocked(uid)+delta < 0 {
				b, f := errResp(http.StatusConflict, "insufficient_funds", "insufficient funds")
				return http.StatusConflict, b, f, true
			}
		}

		recorded := sv.store.nextBatchRecordedAtLocked(items)
		batchID := newID("cb_")
		batchIDPtr := &batchID
		opts := correctionApplyOpts{
			operatorBatch: true, allowSettlement: true,
			batchID: batchIDPtr, sharedRecordedAt: recorded,
		}

		savedRevs := clonePaymentRevisions(sv.store.PaymentRevisions)
		savedBalances := cloneUserBalances(sv.store.Users)
		var pending []PaymentRevision
		for _, it := range items {
			newRev, status, code := sv.store.applyCorrectionLocked(it.paymentID, u, it.expectedRev, it.amount, it.effectiveAt, it.reason, opts)
			if code != "" {
				sv.store.PaymentRevisions = savedRevs
				restoreUserBalances(sv.store.Users, savedBalances)
				if status == httpStatusConflict {
					b, f := errResp(http.StatusConflict, code, code)
					return http.StatusConflict, b, f, true
				}
				if status == httpStatusUnprocessable {
					b, f := errResp(http.StatusUnprocessableEntity, code, code)
					return http.StatusUnprocessableEntity, b, f, true
				}
				b, f := errResp(status, code, code)
				return status, b, f, true
			}
			pending = append(pending, newRev)
		}

		type revOut struct {
			PaymentID         string  `json:"payment_id"`
			Revision          int     `json:"revision"`
			Amount            int64   `json:"amount"`
			EffectiveAt       string  `json:"effective_at"`
			RecordedAt        string  `json:"recorded_at"`
			Reason            string  `json:"reason"`
			CorrectionBatchID *string `json:"correction_batch_id"`
		}
		outs := make([]revOut, len(items))
		for i, it := range items {
			outs[i] = revOut{
				PaymentID: it.paymentID, Revision: pending[i].Revision,
				Amount: pending[i].Amount, EffectiveAt: pending[i].EffectiveAt,
				RecordedAt: pending[i].RecordedAt, Reason: pending[i].Reason,
				CorrectionBatchID: batchIDPtr,
			}
		}
		resp, _ := json.Marshal(map[string]any{
			"correction_batch_id": batchID,
			"recorded_at":         recorded,
			"revisions":           outs,
		})
		return http.StatusCreated, resp, false, true
	})
}

func (s *Store) nextBatchRecordedAtLocked(items []batchCorrectionItem) string {
	var maxRec time.Time
	for _, it := range items {
		cur, ok := s.latestRevisionLocked(it.paymentID)
		if !ok {
			continue
		}
		if t, ok2 := parseTime(cur.RecordedAt); ok2 && (maxRec.IsZero() || t.After(maxRec)) {
			maxRec = t
		}
	}
	if !maxRec.IsZero() {
		minNext := maxRec.Add(time.Second)
		if s.lastMonotonicTime.Before(minNext) {
			s.lastMonotonicTime = minNext
		}
	}
	return s.nextEventTimeRFC3339Locked()
}

func clonePaymentRevisions(src map[string][]PaymentRevision) map[string][]PaymentRevision {
	out := make(map[string][]PaymentRevision, len(src))
	for k, v := range src {
		cp := make([]PaymentRevision, len(v))
		copy(cp, v)
		out[k] = cp
	}
	return out
}

func cloneUserBalances(users map[string]*User) map[string]int64 {
	out := make(map[string]int64, len(users))
	for id, u := range users {
		out[id] = u.Balance
	}
	return out
}

func restoreUserBalances(users map[string]*User, bal map[string]int64) {
	for id, b := range bal {
		if u := users[id]; u != nil {
			u.Balance = b
		}
	}
}

package main

import (
	"encoding/json"
	"net/http"
	"time"
)

func (sv *Server) handleMe(w http.ResponseWriter, r *http.Request) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	q := r.URL.Query()
	asOfRaw, asOfSet, asOfInv := parseOptionalRFC3339Param(q, "as_of")
	if asOfInv {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid as_of")
		return
	}
	knownRaw, knownSet, knownInv := parseOptionalRFC3339Param(q, "known_at")
	if knownInv {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid known_at")
		return
	}
	sv.store.mu.Lock()
	out := sv.meTemporalLocked(u.ID, asOfRaw, asOfSet, knownRaw, knownSet)
	sv.store.mu.Unlock()
	writeJSON(w, http.StatusOK, out)
}

func parseOptionalRFC3339Param(q map[string][]string, key string) (value string, set bool, invalid bool) {
	vals, ok := q[key]
	if !ok {
		return "", false, false
	}
	s := first(vals)
	if s == "" {
		return "", true, true
	}
	if _, ok := parseTime(s); !ok {
		return s, true, true
	}
	return s, true, false
}

func (sv *Server) handleStatement(w http.ResponseWriter, r *http.Request) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	q := r.URL.Query()
	snapTok := first(q["snapshot"])
	if snapTok != "" {
		if _, set, inv := parseOptionalRFC3339Param(q, "from"); set || inv {
			if set {
				writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid from with snapshot")
				return
			}
		}
		if _, set, inv := parseOptionalRFC3339Param(q, "to"); set || inv {
			if set {
				writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid to with snapshot")
				return
			}
		}
		if first(q["from"]) != "" || first(q["to"]) != "" || first(q["known_at"]) != "" {
			writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid params with snapshot")
			return
		}
		limit, offset, ok2 := parseStatementLimitOffset(q)
		if !ok2 {
			writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid pagination")
			return
		}
		sv.store.mu.Lock()
		snap, ok3 := sv.store.getStatementSnapshotLocked(snapTok, u.ID)
		sv.store.mu.Unlock()
		if !ok3 {
			writeError(w, http.StatusNotFound, "not_found", "snapshot not found")
			return
		}
		page, hasMore := paginateStatementEntries(snap.Entries, limit, offset)
		out := map[string]any{
			"opening_balance": snap.OpeningBalance,
			"closing_balance": snap.ClosingBalance,
			"entries":         page,
			"has_more":        hasMore,
			"snapshot":        snapTok,
		}
		writeJSON(w, http.StatusOK, out)
		return
	}

	limit, offset, ok2 := parseStatementLimitOffset(q)
	if !ok2 {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid pagination")
		return
	}
	fromRaw, fromSet, fromInv := parseOptionalRFC3339Param(q, "from")
	if fromInv {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid from")
		return
	}
	toRaw, toSet, toInv := parseOptionalRFC3339Param(q, "to")
	if toInv || (toSet && toRaw == "") {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid to")
		return
	}
	knownRaw, knownSet, knownInv := parseOptionalRFC3339Param(q, "known_at")
	if knownInv {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid known_at")
		return
	}

	var fromT, toT *time.Time
	if fromSet {
		t, _ := parseTime(fromRaw)
		fromT = &t
	}
	if toSet {
		t, _ := parseTime(toRaw)
		toT = &t
	} else {
		t := now()
		toT = &t
	}
	var knownAt *time.Time
	if knownSet {
		t, _ := parseTime(knownRaw)
		knownAt = &t
	}

	sv.store.mu.Lock()
	built := sv.store.buildStatementLocked(u.ID, fromT, toT, knownRaw, knownAt)
	built.Entries = cloneStatementEntries(built.Entries)
	token := newSnapshotToken()
	built.Token = token
	sv.store.StatementSnapshots[token] = &built
	page, hasMore := paginateStatementEntries(built.Entries, limit, offset)
	sv.store.mu.Unlock()

	out := map[string]any{
		"opening_balance": built.OpeningBalance,
		"closing_balance": built.ClosingBalance,
		"entries":         page,
		"has_more":        hasMore,
		"snapshot":        token,
	}
	if knownSet {
		out["known_at"] = knownRaw
	}
	if fromSet {
		out["from"] = fromRaw
	}
	if toSet {
		out["to"] = toRaw
	}
	writeJSON(w, http.StatusOK, out)
}

func (sv *Server) handlePaymentRevisions(w http.ResponseWriter, r *http.Request, pid string) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	sv.store.mu.Lock()
	defer sv.store.mu.Unlock()
	idx := sv.store.findPaymentIndex(pid)
	if idx < 0 {
		writeError(w, http.StatusNotFound, "not_found", "payment not found")
		return
	}
	p := sv.store.Payments[idx]
	if p.FromUserID != u.ID && p.ToUserID != u.ID {
		writeError(w, http.StatusNotFound, "not_found", "payment not found")
		return
	}
	revs := sv.store.PaymentRevisions[pid]
	if revs == nil {
		revs = emptyJSONArray[PaymentRevision]()
	}
	writeJSON(w, http.StatusOK, map[string]any{"revisions": revs})
}

func (sv *Server) handlePaymentCorrection(w http.ResponseWriter, r *http.Request, pid string) {
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
		var body map[string]json.RawMessage
		if err := json.Unmarshal(raw, &body); err != nil {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid json")
			return http.StatusBadRequest, b, f, true
		}
		expRev, expOk, expEk := parseExpectedRevision(body["expected_revision"])
		if expEk == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid expected_revision")
			return http.StatusBadRequest, b, f, true
		}
		if !expOk {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid expected_revision")
			return http.StatusUnprocessableEntity, b, f, true
		}
		amount, amtOk, amtEk := parseNonNegativeAmount(body["amount"])
		if amtEk == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid amount")
			return http.StatusBadRequest, b, f, true
		}
		if !amtOk {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid amount")
			return http.StatusUnprocessableEntity, b, f, true
		}
		effectiveAt, effEk := stringField(body, "effective_at")
		if effEk == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid effective_at")
			return http.StatusBadRequest, b, f, true
		}
		if effEk == errValidation || effectiveAt == "" {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid effective_at")
			return http.StatusUnprocessableEntity, b, f, true
		}
		if _, ok := parseTime(effectiveAt); !ok {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid effective_at")
			return http.StatusUnprocessableEntity, b, f, true
		}
		reason, rEk := stringField(body, "reason")
		if rEk == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid reason")
			return http.StatusBadRequest, b, f, true
		}
		if reason == "" || len(reason) > 200 {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid reason")
			return http.StatusUnprocessableEntity, b, f, true
		}

		sv.store.mu.Lock()
		defer sv.store.mu.Unlock()
		newRev, status, code := sv.store.applyCorrectionLocked(pid, u, expRev, amount, effectiveAt, reason)
		if code != "" {
			if status == httpStatusNotFound {
				b, f := errResp(http.StatusNotFound, code, code)
				return http.StatusNotFound, b, f, true
			}
			if status == httpStatusForbidden {
				b, f := errResp(http.StatusForbidden, code, code)
				return http.StatusForbidden, b, f, true
			}
			if status == httpStatusUnprocessable {
				b, f := errResp(http.StatusUnprocessableEntity, code, code)
				return http.StatusUnprocessableEntity, b, f, true
			}
			b, f := errResp(http.StatusConflict, code, code)
			return http.StatusConflict, b, f, true
		}
		resp, _ := json.Marshal(map[string]any{
			"payment_id": pid, "revision": newRev.Revision, "amount": newRev.Amount,
			"effective_at": newRev.EffectiveAt, "recorded_at": newRev.RecordedAt, "reason": newRev.Reason,
		})
		return http.StatusCreated, resp, false, true
	})
}

func (sv *Server) meTemporalLocked(userID string, asOfRaw string, asOfSet bool, knownRaw string, knownSet bool) map[string]any {
	u := sv.store.Users[userID]
	out := map[string]any{
		"user_id": u.ID, "display_name": u.DisplayName, "handle": u.Handle,
		"currency": sv.store.Currency, "minor_units": sv.store.MinorUnits,
	}
	var knownAt *time.Time
	if knownSet {
		t, _ := parseTime(knownRaw)
		knownAt = &t
		out["known_at"] = knownRaw
	}
	var asOf *time.Time
	if asOfSet {
		t, _ := parseTime(asOfRaw)
		asOf = &t
		out["as_of"] = asOfRaw
	}

	if !asOfSet && !knownSet {
		held := sv.store.heldForUserLocked(userID)
		out["balance"] = u.Balance
		out["total"] = u.Balance
		out["available"] = sv.store.availableForUserLocked(userID)
		out["held"] = held
		return out
	}

	at := now()
	if asOfSet {
		at = *asOf
	}
	bal := sv.store.balanceAtInstantLocked(userID, at, knownAt, "", nil)
	held := sv.store.heldForUserAtLocked(userID, at, knownAt)
	out["balance"] = bal
	out["total"] = bal
	out["held"] = held
	avail := bal - held
	if avail < 0 {
		avail = 0
	}
	out["available"] = avail
	return out
}

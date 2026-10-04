package main

import (
	"encoding/json"
	"net/http"
	"sort"
	"time"
)

func (sv *Server) handleCreateAuthorization(w http.ResponseWriter, r *http.Request) {
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
		toHandle, ek := stringField(body, "to_handle")
		if ek == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid to_handle")
			return http.StatusBadRequest, b, f, true
		}
		if ek == errValidation || toHandle == "" {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "to_handle required")
			return http.StatusUnprocessableEntity, b, f, true
		}
		amount, amtOk, ek := parseIntegralAmount(body["amount"])
		if ek == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid amount type")
			return http.StatusBadRequest, b, f, true
		}
		if !amtOk {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid amount")
			return http.StatusUnprocessableEntity, b, f, true
		}
		note, ek := parseNoteField(body, "note")
		if ek == errValidation {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid note")
			return http.StatusUnprocessableEntity, b, f, true
		}
		if ek == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid note")
			return http.StatusBadRequest, b, f, true
		}
		vis, ek := optionalStringField(body, "visibility", "public")
		if ek == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid visibility")
			return http.StatusBadRequest, b, f, true
		}
		if vis != "public" && vis != "private" {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid visibility")
			return http.StatusUnprocessableEntity, b, f, true
		}

		sv.store.mu.Lock()
		defer sv.store.mu.Unlock()
		from := sv.store.Users[u.ID]
		toID, ok := sv.store.UsersByHandle[toHandle]
		if !ok {
			b, f := errResp(http.StatusNotFound, "not_found", "handle not found")
			return http.StatusNotFound, b, f, true
		}
		to := sv.store.Users[toID]
		if from.ID == to.ID {
			b, f := errResp(http.StatusUnprocessableEntity, "self_payment", "self payment")
			return http.StatusUnprocessableEntity, b, f, true
		}
		if sv.store.availableForUserLocked(from.ID) < amount {
			b, f := errResp(http.StatusConflict, "insufficient_funds", "insufficient funds")
			return http.StatusConflict, b, f, true
		}
		created := nowRFC3339()
		createdT, _ := parseTime(created)
		expires := mustFormatTime(createdT.Add(time.Duration(sv.store.AuthorizationTTLSeconds) * time.Second))
		aid := newID("a_")
		a := Authorization{
			AuthorizationID: aid, FromUserID: from.ID, FromHandle: from.Handle,
			ToUserID: to.ID, ToHandle: to.Handle, Amount: amount,
			CapturedAmount: 0, Note: note, Visibility: vis, Status: "open",
			ExpiresAt: expires, CreatedAt: created, PaymentID: nil, PaymentIDs: []string{},
		}
		sv.store.Authorizations = append(sv.store.Authorizations, a)
		// open hold — no closed_at
		resp, _ := json.Marshal(authResponse(a, sv.store.Currency))
		return http.StatusCreated, resp, false, true
	})
}

func parseCaptureBody(raw []byte) (captureAmount *int64, final bool, malformed bool, invalidAmount bool) {
	final = true
	if len(raw) == 0 {
		return nil, true, false, false
	}
	var body map[string]json.RawMessage
	if err := json.Unmarshal(raw, &body); err != nil {
		return nil, true, true, false
	}
	if v, ok := body["final"]; ok {
		var fb bool
		if err := json.Unmarshal(v, &fb); err != nil {
			return nil, true, true, false
		}
		final = fb
	}
	if v, ok := body["amount"]; ok {
		amt, okAmt, ek := parseIntegralAmount(v)
		if ek == errMalformed {
			return nil, true, true, false
		}
		if !okAmt {
			return nil, final, false, true
		}
		return &amt, final, false, false
	}
	return nil, final, false, false
}

func (sv *Server) handleCaptureAuthorization(w http.ResponseWriter, r *http.Request, authID string) {
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
		captureAmtPtr, final, badJSON, invalidAmount := parseCaptureBody(raw)
		if badJSON {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid json")
			return http.StatusBadRequest, b, f, true
		}
		if invalidAmount {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid amount")
			return http.StatusUnprocessableEntity, b, f, true
		}
		if captureAmtPtr != nil && *captureAmtPtr < 1 {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid amount")
			return http.StatusUnprocessableEntity, b, f, true
		}

		sv.store.mu.Lock()
		defer sv.store.mu.Unlock()
		sv.store.refreshAuthorizationExpiryLocked()
		a, _ := sv.store.findAuthorization(authID)
		if a == nil {
			b, f := errResp(http.StatusNotFound, "not_found", "authorization not found")
			return http.StatusNotFound, b, f, true
		}
		if a.ToUserID != u.ID {
			b, f := errResp(http.StatusForbidden, "forbidden", "not receiver")
			return http.StatusForbidden, b, f, true
		}
		if a.Status == "open" {
			exp, ok := parseTime(a.ExpiresAt)
			if ok && !exp.After(now()) {
				a.Status = "expired"
			}
		}
		if a.Status == "expired" {
			b, f := errResp(http.StatusConflict, "authorization_expired", "authorization expired")
			return http.StatusConflict, b, f, true
		}
		if a.Status != "open" {
			b, f := errResp(http.StatusConflict, "authorization_not_open", "authorization not open")
			return http.StatusConflict, b, f, true
		}
		remaining := a.Amount - a.CapturedAmount
		captureAmt := remaining
		if captureAmtPtr != nil {
			captureAmt = *captureAmtPtr
		}
		if captureAmt > remaining {
			b, f := errResp(http.StatusUnprocessableEntity, "capture_exceeds_authorization", "capture exceeds authorization")
			return http.StatusUnprocessableEntity, b, f, true
		}
		from := sv.store.Users[a.FromUserID]
		to := sv.store.Users[a.ToUserID]
		if from.Balance < captureAmt {
			b, f := errResp(http.StatusConflict, "insufficient_funds", "insufficient funds")
			return http.StatusConflict, b, f, true
		}
		from.Balance -= captureAmt
		to.Balance += captureAmt
		pid := newID("p_")
		aid := a.AuthorizationID
		p := Payment{
			PaymentID: pid, FromUserID: from.ID, FromHandle: from.Handle,
			ToUserID: to.ID, ToHandle: to.Handle, Amount: captureAmt,
			Currency: sv.store.Currency, Note: a.Note, Visibility: a.Visibility,
			RequestID: nil, AuthorizationID: &aid, CreatedAt: nowRFC3339(),
		}
		sv.store.registerPaymentLocked(p, false)
		a.CapturedAmount += captureAmt
		a.PaymentID = &pid
		if a.PaymentIDs == nil {
			a.PaymentIDs = []string{}
		}
		a.PaymentIDs = append(a.PaymentIDs, pid)
		newRemaining := a.Amount - a.CapturedAmount
		closeAuth := final || newRemaining == 0
		if closeAuth {
			if a.Status == "open" {
				a.Status = "captured"
			}
			sv.store.setAuthClosedLocked(a, p.CreatedAt)
		}
		resp, _ := json.Marshal(p)
		return http.StatusCreated, resp, false, true
	})
}

func (sv *Server) handleVoidAuthorization(w http.ResponseWriter, r *http.Request, authID string) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	sv.store.mu.Lock()
	defer sv.store.mu.Unlock()
	sv.store.refreshAuthorizationExpiryLocked()
	a, _ := sv.store.findAuthorization(authID)
	if a == nil {
		writeError(w, http.StatusNotFound, "not_found", "authorization not found")
		return
	}
	if a.FromUserID != u.ID {
		writeError(w, http.StatusForbidden, "forbidden", "not payer")
		return
	}
	if a.Status == "voided" {
		writeJSON(w, http.StatusOK, authResponse(*a, sv.store.Currency))
		return
	}
	if a.Status != "open" {
		writeError(w, http.StatusConflict, "authorization_not_open", "authorization not open")
		return
	}
	a.Status = "voided"
	closed := nowRFC3339()
	sv.store.setAuthClosedLocked(a, closed)
	writeJSON(w, http.StatusOK, authResponse(*a, sv.store.Currency))
}

func (sv *Server) handleListAuthorizations(w http.ResponseWriter, r *http.Request) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	limit, offset, ok2 := parseLimitOffset(r.URL.Query())
	if !ok2 {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid pagination")
		return
	}
	dir := first(r.URL.Query()["direction"])
	statusF := first(r.URL.Query()["status"])
	if dir != "" && dir != "incoming" && dir != "outgoing" {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid direction")
		return
	}
	if statusF != "" && statusF != "open" && statusF != "captured" && statusF != "voided" && statusF != "expired" {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid status")
		return
	}

	sv.store.mu.Lock()
	defer sv.store.mu.Unlock()
	sv.store.refreshAuthorizationExpiryLocked()
	var filtered []Authorization
	for _, a := range sv.store.Authorizations {
		if a.FromUserID != u.ID && a.ToUserID != u.ID {
			continue
		}
		if dir == "incoming" && a.ToUserID != u.ID {
			continue
		}
		if dir == "outgoing" && a.FromUserID != u.ID {
			continue
		}
		st := a.Status
		if statusF != "" && st != statusF {
			continue
		}
		filtered = append(filtered, a)
	}
	sort.Slice(filtered, func(i, j int) bool {
		return filtered[i].CreatedAt > filtered[j].CreatedAt
	})
	hasMore := len(filtered) > offset+limit
	if offset > len(filtered) {
		filtered = emptyJSONArray[Authorization]()
	} else {
		end := offset + limit
		if end > len(filtered) {
			end = len(filtered)
		}
		filtered = filtered[offset:end]
	}
	if filtered == nil {
		filtered = emptyJSONArray[Authorization]()
	}
	out := make([]map[string]any, len(filtered))
	for i, a := range filtered {
		out[i] = authResponse(a, sv.store.Currency)
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"authorizations": out, "has_more": hasMore,
	})
}

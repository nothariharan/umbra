package main

import (
	"encoding/json"
	"io"
	"net/http"
	"sort"
	"strings"
	"unicode/utf8"
)

type Server struct {
	store *Store
}

func (sv *Server) authUser(r *http.Request) (*User, bool) {
	h := r.Header.Get("Authorization")
	if !strings.HasPrefix(h, "Bearer ") {
		return nil, false
	}
	token := strings.TrimSpace(strings.TrimPrefix(h, "Bearer "))
	if token == "" {
		return nil, false
	}
	u, ok := sv.store.userByToken(token)
	return u, ok
}

func (sv *Server) requireAuth(w http.ResponseWriter, r *http.Request) (*User, bool) {
	u, ok := sv.authUser(r)
	if !ok {
		writeError(w, http.StatusUnauthorized, "unauthenticated", "authentication required")
		return nil, false
	}
	return u, true
}

func readBody(r *http.Request) ([]byte, bool) {
	raw, err := io.ReadAll(r.Body)
	if err != nil {
		return nil, false
	}
	return raw, true
}

type idemHandler func(w http.ResponseWriter, raw []byte) (status int, resp []byte, failed4xx bool, done bool)

func (sv *Server) runIdempotent(w http.ResponseWriter, r *http.Request, u *User, raw []byte, fn idemHandler) {
	idemKey, ok := checkIdempotencyHeader(w, r)
	if !ok {
		return
	}
	bodyHash := canonicalBodyHash(raw)
	fullKey := idempotencyKey(u.ID, r.Method, r.URL.Path, idemKey)
	res, commit, abort, ok2 := sv.store.beginIdempotency(fullKey, bodyHash)
	if !ok2 {
		writeError(w, http.StatusConflict, "idempotency_key_reuse", "key reused with different body")
		return
	}
	if res.replay {
		writeIdemBody(w, res.status, res.body)
		return
	}
	status, resp, failed4xx, done := fn(w, raw)
	if !done {
		if abort != nil {
			abort()
		}
		return
	}
	commit(status, resp, failed4xx)
	writeIdemBody(w, status, resp)
}

func (sv *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (sv *Server) handleReset(w http.ResponseWriter, r *http.Request) {
	raw, ok := readBody(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid body")
		return
	}
	var f fixture
	if err := json.Unmarshal(raw, &f); err != nil {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid json")
		return
	}
	if err := sv.store.applyFixture(f); err != nil {
		if _, ok := err.(fixtureError); ok {
			writeError(w, http.StatusUnprocessableEntity, "validation_failed", err.Error())
			return
		}
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "fixture invalid")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (sv *Server) handleExport(w http.ResponseWriter, _ *http.Request) {
	state := sv.store.exportState()
	writeJSON(w, http.StatusOK, map[string]any{
		"track":          "pocketful",
		"format_version": 1,
		"state":          state,
	})
}

func (sv *Server) handleImport(w http.ResponseWriter, r *http.Request) {
	raw, ok := readBody(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid body")
		return
	}
	var doc struct {
		Track         string          `json:"track"`
		FormatVersion int             `json:"format_version"`
		State         json.RawMessage `json:"state"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid export")
		return
	}
	if doc.Track != "pocketful" || doc.FormatVersion != 1 || len(doc.State) == 0 {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid export")
		return
	}
	var snap storeSnapshot
	if err := json.Unmarshal(doc.State, &snap); err != nil {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid state")
		return
	}
	sv.store.mu.Lock()
	sv.store.loadSnapshot(snap)
	sv.store.mu.Unlock()
	w.WriteHeader(http.StatusNoContent)
}

func (sv *Server) handleSignup(w http.ResponseWriter, r *http.Request) {
	raw, ok := readBody(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid body")
		return
	}
	var body map[string]json.RawMessage
	if err := json.Unmarshal(raw, &body); err != nil {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid json")
		return
	}
	email, ek := stringField(body, "email")
	if ek == errMalformed {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid email type")
		return
	}
	if !validEmail(email) {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid email")
		return
	}
	pw, ek := stringField(body, "password")
	if ek == errMalformed {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid password type")
		return
	}
	if utf8.RuneCountInString(pw) < 8 {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "password too short")
		return
	}
	dn, ek := stringField(body, "display_name")
	if ek == errMalformed {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid display_name type")
		return
	}
	if dn == "" {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "display_name required")
		return
	}

	handle := deriveHandle(email)
	sv.store.mu.Lock()
	defer sv.store.mu.Unlock()
	if _, ok := sv.store.UsersByEmail[email]; ok {
		writeError(w, http.StatusConflict, "email_taken", "email already registered")
		return
	}
	if _, ok := sv.store.UsersByHandle[handle]; ok {
		writeError(w, http.StatusConflict, "handle_taken", "handle already taken")
		return
	}
	ph, err := hashPassword(pw)
	if err != nil {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "could not hash password")
		return
	}
	id := newID("u_")
	u := &User{
		ID: id, Email: email, PasswordHash: ph, DisplayName: dn, Handle: handle, Balance: 0,
	}
	sv.store.Users[id] = u
	sv.store.UsersByEmail[email] = id
	sv.store.UsersByHandle[handle] = id
	if sv.store.OpeningBalances == nil {
		sv.store.OpeningBalances = make(map[string]int64)
	}
	sv.store.OpeningBalances[id] = 0
	tok := newToken()
	sv.store.Tokens[tok] = id
	writeJSON(w, http.StatusCreated, map[string]any{
		"user_id": id, "display_name": dn, "token": tok,
	})
}

func (sv *Server) handleLogin(w http.ResponseWriter, r *http.Request) {
	raw, ok := readBody(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid body")
		return
	}
	var body map[string]json.RawMessage
	if err := json.Unmarshal(raw, &body); err != nil {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid json")
		return
	}
	email, ek := stringField(body, "email")
	if ek == errMalformed {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid email type")
		return
	}
	pw, ek := stringField(body, "password")
	if ek == errMalformed {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid password type")
		return
	}
	sv.store.mu.Lock()
	defer sv.store.mu.Unlock()
	uid, ok := sv.store.UsersByEmail[email]
	if !ok {
		writeError(w, http.StatusUnauthorized, "unauthenticated", "invalid credentials")
		return
	}
	u := sv.store.Users[uid]
	if !checkPassword(u.PasswordHash, pw) {
		writeError(w, http.StatusUnauthorized, "unauthenticated", "invalid credentials")
		return
	}
	tok := newToken()
	sv.store.Tokens[tok] = uid
	writeJSON(w, http.StatusOK, map[string]any{
		"user_id": u.ID, "display_name": u.DisplayName, "token": tok,
	})
}

func stringField(body map[string]json.RawMessage, key string) (string, errorKind) {
	raw, ok := body[key]
	if !ok {
		return "", errValidation
	}
	var s string
	if err := json.Unmarshal(raw, &s); err != nil {
		return "", errMalformed
	}
	return s, errNone
}

func optionalStringField(body map[string]json.RawMessage, key, def string) (string, errorKind) {
	raw, ok := body[key]
	if !ok {
		return def, errNone
	}
	var s string
	if err := json.Unmarshal(raw, &s); err != nil {
		return "", errMalformed
	}
	return s, errNone
}

func errResp(status int, code, msg string) ([]byte, bool) {
	e := apiError{}
	e.Error.Code = code
	e.Error.Message = msg
	b, _ := json.Marshal(e)
	return b, status >= 400 && status < 500
}

func (sv *Server) handlePayments(w http.ResponseWriter, r *http.Request) {
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
		from.Balance -= amount
		to.Balance += amount
		pid := newID("p_")
		created := sv.store.nextEventTimeRFC3339Locked()
		p := Payment{
			PaymentID: pid, FromUserID: from.ID, FromHandle: from.Handle,
			ToUserID: to.ID, ToHandle: to.Handle, Amount: amount,
			Currency: sv.store.Currency, Note: note, Visibility: vis,
			RequestID: nil, AuthorizationID: nil, CreatedAt: created,
		}
		sv.store.registerPaymentLocked(p, false)
		resp, _ := json.Marshal(p)
		return http.StatusCreated, resp, false, true
	})
}

func paymentCreatedAtAsc(a, b Payment) bool {
	ta, oka := parseTime(a.CreatedAt)
	tb, okb := parseTime(b.CreatedAt)
	if oka && okb {
		if ta.Equal(tb) {
			return a.PaymentID < b.PaymentID
		}
		return ta.Before(tb)
	}
	return a.CreatedAt < b.CreatedAt
}

func (sv *Server) handleCreateRequest(w http.ResponseWriter, r *http.Request) {
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
		payerHandle, ek := stringField(body, "payer_handle")
		if ek == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid payer_handle")
			return http.StatusBadRequest, b, f, true
		}
		if ek == errValidation || payerHandle == "" {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "payer_handle required")
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

		sv.store.mu.Lock()
		defer sv.store.mu.Unlock()
		reqr := sv.store.Users[u.ID]
		payerID, ok := sv.store.UsersByHandle[payerHandle]
		if !ok {
			b, f := errResp(http.StatusNotFound, "not_found", "handle not found")
			return http.StatusNotFound, b, f, true
		}
		payer := sv.store.Users[payerID]
		if reqr.ID == payer.ID {
			b, f := errResp(http.StatusUnprocessableEntity, "self_request", "self request")
			return http.StatusUnprocessableEntity, b, f, true
		}
		rid := newID("rq_")
		mr := MoneyRequest{
			RequestID: rid, RequesterID: reqr.ID, RequesterHandle: reqr.Handle,
			PayerID: payer.ID, PayerHandle: payer.Handle, Amount: amount,
			Currency: sv.store.Currency, Note: note, Status: "pending",
			PaymentID: nil, CreatedAt: nowRFC3339(),
		}
		sv.store.Requests = append(sv.store.Requests, mr)
		resp, _ := json.Marshal(mr)
		return http.StatusCreated, resp, false, true
	})
}

func (sv *Server) findRequest(id string) (*MoneyRequest, int) {
	for i := range sv.store.Requests {
		if sv.store.Requests[i].RequestID == id {
			return &sv.store.Requests[i], i
		}
	}
	return nil, -1
}

func (sv *Server) handlePayRequest(w http.ResponseWriter, r *http.Request, reqID string) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	path := r.URL.Path
	raw, ok := readBody(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "malformed_request", "invalid body")
		return
	}
	sv.runIdempotent(w, r, u, raw, func(w http.ResponseWriter, raw []byte) (int, []byte, bool, bool) {
		_ = path
		parseRaw := raw
		if len(parseRaw) == 0 {
			parseRaw = []byte("{}")
		}
		var body map[string]json.RawMessage
		if err := json.Unmarshal(parseRaw, &body); err != nil {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid json")
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
		mr, _ := sv.findRequest(reqID)
		if mr == nil {
			b, f := errResp(http.StatusNotFound, "not_found", "request not found")
			return http.StatusNotFound, b, f, true
		}
		if mr.PayerID != u.ID {
			b, f := errResp(http.StatusForbidden, "forbidden", "not payer")
			return http.StatusForbidden, b, f, true
		}
		if mr.Status != "pending" {
			b, f := errResp(http.StatusConflict, "request_not_pending", "request not pending")
			return http.StatusConflict, b, f, true
		}
		payer := sv.store.Users[mr.PayerID]
		reqr := sv.store.Users[mr.RequesterID]
		if sv.store.availableForUserLocked(payer.ID) < mr.Amount {
			b, f := errResp(http.StatusConflict, "insufficient_funds", "insufficient funds")
			return http.StatusConflict, b, f, true
		}
		payer.Balance -= mr.Amount
		reqr.Balance += mr.Amount
		pid := newID("p_")
		rid := mr.RequestID
		p := Payment{
			PaymentID: pid, FromUserID: payer.ID, FromHandle: payer.Handle,
			ToUserID: reqr.ID, ToHandle: reqr.Handle, Amount: mr.Amount,
			Currency: sv.store.Currency, Note: mr.Note, Visibility: vis,
			RequestID: &rid, AuthorizationID: nil, CreatedAt: nowRFC3339(),
		}
		sv.store.registerPaymentLocked(p, false)
		mr.Status = "paid"
		mr.PaymentID = &pid
		resp, _ := json.Marshal(p)
		return http.StatusCreated, resp, false, true
	})
}

func (sv *Server) handleDeclineRequest(w http.ResponseWriter, r *http.Request, reqID string) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	sv.store.mu.Lock()
	defer sv.store.mu.Unlock()
	mr, _ := sv.findRequest(reqID)
	if mr == nil {
		writeError(w, http.StatusNotFound, "not_found", "request not found")
		return
	}
	if mr.PayerID != u.ID {
		writeError(w, http.StatusForbidden, "forbidden", "not payer")
		return
	}
	if mr.Status == "declined" {
		writeJSON(w, http.StatusOK, mr)
		return
	}
	if mr.Status != "pending" {
		writeError(w, http.StatusConflict, "request_not_pending", "request not pending")
		return
	}
	mr.Status = "declined"
	writeJSON(w, http.StatusOK, mr)
}

func (sv *Server) handleCancelRequest(w http.ResponseWriter, r *http.Request, reqID string) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	sv.store.mu.Lock()
	defer sv.store.mu.Unlock()
	mr, _ := sv.findRequest(reqID)
	if mr == nil {
		writeError(w, http.StatusNotFound, "not_found", "request not found")
		return
	}
	if mr.RequesterID != u.ID {
		writeError(w, http.StatusForbidden, "forbidden", "not requester")
		return
	}
	if mr.Status == "cancelled" {
		writeJSON(w, http.StatusOK, mr)
		return
	}
	if mr.Status != "pending" {
		writeError(w, http.StatusConflict, "request_not_pending", "request not pending")
		return
	}
	mr.Status = "cancelled"
	writeJSON(w, http.StatusOK, mr)
}

func (sv *Server) handleListRequests(w http.ResponseWriter, r *http.Request) {
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
	if statusF != "" && statusF != "pending" && statusF != "paid" && statusF != "declined" && statusF != "cancelled" {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid status")
		return
	}

	sv.store.mu.Lock()
	defer sv.store.mu.Unlock()
	var filtered []MoneyRequest
	for _, mr := range sv.store.Requests {
		if mr.RequesterID != u.ID && mr.PayerID != u.ID {
			continue
		}
		if dir == "incoming" && mr.PayerID != u.ID {
			continue
		}
		if dir == "outgoing" && mr.RequesterID != u.ID {
			continue
		}
		if statusF != "" && mr.Status != statusF {
			continue
		}
		filtered = append(filtered, mr)
	}
	sort.Slice(filtered, func(i, j int) bool {
		return filtered[i].CreatedAt > filtered[j].CreatedAt
	})
	hasMore := len(filtered) > offset+limit
	if offset > len(filtered) {
		filtered = emptyJSONArray[MoneyRequest]()
	} else {
		end := offset + limit
		if end > len(filtered) {
			end = len(filtered)
		}
		filtered = filtered[offset:end]
	}
	if filtered == nil {
		filtered = emptyJSONArray[MoneyRequest]()
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"requests": filtered, "has_more": hasMore,
	})
}

func (sv *Server) handleSplits(w http.ResponseWriter, r *http.Request) {
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
		var handles []string
		if err := json.Unmarshal(body["participant_handles"], &handles); err != nil {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid participant_handles")
			return http.StatusBadRequest, b, f, true
		}
		if len(handles) == 0 {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "participants required")
			return http.StatusUnprocessableEntity, b, f, true
		}
		seen := map[string]struct{}{}
		for _, h := range handles {
			if _, ok := seen[h]; ok {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "duplicate participant")
				return http.StatusUnprocessableEntity, b, f, true
			}
			seen[h] = struct{}{}
		}

		sv.store.mu.Lock()
		defer sv.store.mu.Unlock()
		reqr := sv.store.Users[u.ID]
		shares := splitShares(amount, len(handles))
		shareObjs := make([]map[string]any, len(handles))
		for i, h := range handles {
			shareObjs[i] = map[string]any{"handle": h, "amount": shares[i]}
		}
		created := emptyJSONArray[MoneyRequest]()
		for i, h := range handles {
			uid, ok := sv.store.UsersByHandle[h]
			if !ok {
				b, f := errResp(http.StatusNotFound, "not_found", "handle not found")
				return http.StatusNotFound, b, f, true
			}
			if uid == reqr.ID {
				continue
			}
			payer := sv.store.Users[uid]
			share := shares[i]
			rid := newID("rq_")
			mr := MoneyRequest{
				RequestID: rid, RequesterID: reqr.ID, RequesterHandle: reqr.Handle,
				PayerID: payer.ID, PayerHandle: payer.Handle, Amount: share,
				Currency: sv.store.Currency, Note: note, Status: "pending",
				PaymentID: nil, CreatedAt: nowRFC3339(),
			}
			sv.store.Requests = append(sv.store.Requests, mr)
			created = append(created, mr)
		}
		splitID := newID("sp_")
		createdAt := nowRFC3339()
		out := map[string]any{
			"split_id": splitID, "amount": amount, "currency": sv.store.Currency,
			"note": note, "participant_handles": handles, "shares": shareObjs, "requests": created,
			"created_at": createdAt,
		}
		resp, _ := json.Marshal(out)
		return http.StatusCreated, resp, false, true
	})
}

func (sv *Server) handleActivity(w http.ResponseWriter, r *http.Request) {
	u, ok := sv.requireAuth(w, r)
	if !ok {
		return
	}
	limit, offset, ok2 := parseLimitOffset(r.URL.Query())
	if !ok2 {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid pagination")
		return
	}
	sv.store.mu.Lock()
	defer sv.store.mu.Unlock()
	var visible []Payment
	for _, p := range sv.store.Payments {
		if p.Visibility == "public" || p.FromUserID == u.ID || p.ToUserID == u.ID {
			visible = append(visible, p)
		}
	}
	sort.Slice(visible, func(i, j int) bool {
		return paymentCreatedAtAsc(visible[i], visible[j])
	})
	hasMore := len(visible) > offset+limit
	if offset > len(visible) {
		visible = emptyJSONArray[Payment]()
	} else {
		end := offset + limit
		if end > len(visible) {
			end = len(visible)
		}
		visible = visible[offset:end]
	}
	if visible == nil {
		visible = emptyJSONArray[Payment]()
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"payments": visible, "has_more": hasMore,
	})
}

func (sv *Server) handleSettlements(w http.ResponseWriter, r *http.Request) {
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
		rawTransfers, ok := body["transfers"]
		if !ok || len(rawTransfers) == 0 {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid transfers")
			return http.StatusUnprocessableEntity, b, f, true
		}
		var transfers []map[string]json.RawMessage
		if err := json.Unmarshal(rawTransfers, &transfers); err != nil {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid transfers")
			return http.StatusUnprocessableEntity, b, f, true
		}
		if len(transfers) < 1 || len(transfers) > 32 {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid transfer count")
			return http.StatusUnprocessableEntity, b, f, true
		}

		type xfer struct {
			from, to string
			amount   int64
			note     string
			vis      string
		}
		var xfers []xfer
		net := map[string]int64{}
		for _, t := range transfers {
			fh, ek := stringField(t, "from_handle")
			if ek != errNone {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid from_handle")
				return http.StatusUnprocessableEntity, b, f, true
			}
			th, ek := stringField(t, "to_handle")
			if ek != errNone {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid to_handle")
				return http.StatusUnprocessableEntity, b, f, true
			}
			if fh == th {
				b, f := errResp(http.StatusUnprocessableEntity, "self_payment", "self payment")
				return http.StatusUnprocessableEntity, b, f, true
			}
			amount, amtOk, ek := parseIntegralAmount(t["amount"])
			if ek == errMalformed || !amtOk {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid amount")
				return http.StatusUnprocessableEntity, b, f, true
			}
			note, ek := parseNoteField(t, "note")
			if ek == errValidation {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid note")
				return http.StatusUnprocessableEntity, b, f, true
			}
			if ek == errMalformed {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid note")
				return http.StatusUnprocessableEntity, b, f, true
			}
			vis, ek := optionalStringField(t, "visibility", "public")
			if ek == errMalformed {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid visibility")
				return http.StatusUnprocessableEntity, b, f, true
			}
			if vis != "public" && vis != "private" {
				b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid visibility")
				return http.StatusUnprocessableEntity, b, f, true
			}
			fromID, ok := sv.store.UsersByHandle[fh]
			if !ok {
				b, f := errResp(http.StatusNotFound, "not_found", "handle not found")
				return http.StatusNotFound, b, f, true
			}
			toID, ok := sv.store.UsersByHandle[th]
			if !ok {
				b, f := errResp(http.StatusNotFound, "not_found", "handle not found")
				return http.StatusNotFound, b, f, true
			}
			net[fromID] -= amount
			net[toID] += amount
			xfers = append(xfers, xfer{from: fromID, to: toID, amount: amount, note: note, vis: vis})
		}
		for uid, delta := range net {
			if delta >= 0 {
				continue
			}
			if sv.store.availableForUserLocked(uid)+delta < 0 {
				b, f := errResp(http.StatusConflict, "insufficient_funds", "insufficient funds")
				return http.StatusConflict, b, f, true
			}
		}
		sid := newID("st_")
		committed := nowRFC3339()
		var payments []Payment
		for _, x := range xfers {
			from := sv.store.Users[x.from]
			to := sv.store.Users[x.to]
			from.Balance -= x.amount
			to.Balance += x.amount
			pid := newID("p_")
			p := Payment{
				PaymentID: pid, FromUserID: from.ID, FromHandle: from.Handle,
				ToUserID: to.ID, ToHandle: to.Handle, Amount: x.amount,
				Currency: sv.store.Currency, Note: x.note, Visibility: x.vis,
				RequestID: nil, AuthorizationID: nil, SettlementID: &sid, CreatedAt: committed,
			}
			sv.store.registerPaymentLocked(p, false)
			payments = append(payments, p)
		}
		out := map[string]any{
			"settlement_id": sid, "committed_at": committed, "payments": payments,
		}
		resp, _ := json.Marshal(out)
		return http.StatusCreated, resp, false, true
	})
}

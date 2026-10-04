package main

import (
	"encoding/json"
	"net/http"
)

func (s *Store) applyRefundLocked(targetID string, receiver *User, amount int64) (Payment, int, string) {
	idx := s.findPaymentIndex(targetID)
	if idx < 0 {
		return Payment{}, httpStatusNotFound, "not_found"
	}
	target := s.Payments[idx]
	if target.ToUserID != receiver.ID {
		return Payment{}, httpStatusForbidden, "forbidden"
	}
	if target.RefundOf != nil {
		return Payment{}, httpStatusUnprocessable, "invalid_refund_target"
	}
	cur, ok := s.latestRevisionLocked(targetID)
	if !ok {
		return Payment{}, httpStatusNotFound, "not_found"
	}
	refunded := s.totalRefundedLocked(targetID)
	if refunded+amount > cur.Amount {
		return Payment{}, httpStatusUnprocessable, "refund_exceeds_payment"
	}
	if s.availableForUserLocked(receiver.ID) < amount {
		return Payment{}, httpStatusConflict, "insufficient_funds"
	}

	from := s.Users[target.ToUserID]
	to := s.Users[target.FromUserID]
	from.Balance -= amount
	to.Balance += amount
	pid := newID("p_")
	ro := targetID
	p := Payment{
		PaymentID: pid, FromUserID: from.ID, FromHandle: from.Handle,
		ToUserID: to.ID, ToHandle: to.Handle, Amount: amount,
		Currency: s.Currency, Note: target.Note, Visibility: target.Visibility,
		RequestID: nil, AuthorizationID: nil, SettlementID: nil,
		RefundOf: &ro, CreatedAt: nowRFC3339(),
	}
	s.registerPaymentLocked(p, false)
	return p, httpStatusCreated, ""
}

func (sv *Server) handlePaymentRefund(w http.ResponseWriter, r *http.Request, targetID string) {
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
		amount, amtOk, amtEk := parseNonNegativeAmount(body["amount"])
		if amtEk == errMalformed {
			b, f := errResp(http.StatusBadRequest, "malformed_request", "invalid amount")
			return http.StatusBadRequest, b, f, true
		}
		if !amtOk || amount == 0 {
			b, f := errResp(http.StatusUnprocessableEntity, "validation_failed", "invalid amount")
			return http.StatusUnprocessableEntity, b, f, true
		}

		sv.store.mu.Lock()
		defer sv.store.mu.Unlock()
		p, status, code := sv.store.applyRefundLocked(targetID, u, amount)
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
		resp, _ := json.Marshal(p)
		return http.StatusCreated, resp, false, true
	})
}

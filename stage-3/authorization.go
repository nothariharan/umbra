package main

import (
	"encoding/json"
	"time"
)

type Authorization struct {
	AuthorizationID string   `json:"authorization_id"`
	FromUserID      string   `json:"from_user_id"`
	FromHandle      string   `json:"from_handle"`
	ToUserID        string   `json:"to_user_id"`
	ToHandle        string   `json:"to_handle"`
	Amount          int64    `json:"amount"`
	CapturedAmount  int64    `json:"captured_amount"`
	Note            string   `json:"note"`
	Visibility      string   `json:"visibility"`
	Status          string   `json:"status"`
	ExpiresAt       string   `json:"expires_at"`
	CreatedAt       string   `json:"created_at"`
	PaymentID       *string  `json:"payment_id"`
	PaymentIDs      []string `json:"payment_ids"`
	ClosedAt        *string  `json:"closed_at"`
}

func (a Authorization) remainingAmount() int64 {
	if a.Status != "open" {
		return 0
	}
	return a.Amount - a.CapturedAmount
}

func (s *Store) refreshAuthorizationExpiryLocked() {
	nowT := now()
	for i := range s.Authorizations {
		a := &s.Authorizations[i]
		if a.Status != "open" {
			continue
		}
		exp, ok := parseTime(a.ExpiresAt)
		if !ok {
			continue
		}
		if !exp.After(nowT) {
			a.Status = "expired"
			if a.ClosedAt == nil || *a.ClosedAt == "" {
				w := mustFormatTime(exp)
				a.ClosedAt = &w
			}
		}
	}
}

func (s *Store) heldForUserLocked(userID string) int64 {
	s.refreshAuthorizationExpiryLocked()
	var held int64
	for _, a := range s.Authorizations {
		if a.FromUserID != userID || a.Status != "open" {
			continue
		}
		rem := a.Amount - a.CapturedAmount
		if rem > 0 {
			held += rem
		}
	}
	return held
}

func (s *Store) availableForUserLocked(userID string) int64 {
	u := s.Users[userID]
	if u == nil {
		return 0
	}
	held := s.heldForUserLocked(userID)
	av := u.Balance - held
	if av < 0 {
		return 0
	}
	return av
}

func (s *Store) findAuthorization(id string) (*Authorization, int) {
	for i := range s.Authorizations {
		if s.Authorizations[i].AuthorizationID == id {
			return &s.Authorizations[i], i
		}
	}
	return nil, -1
}

func authResponse(a Authorization, currency string) map[string]any {
	rem := int64(0)
	if a.Status == "open" {
		rem = a.Amount - a.CapturedAmount
		if rem < 0 {
			rem = 0
		}
	}
	pids := a.PaymentIDs
	if pids == nil {
		pids = []string{}
	}
	return map[string]any{
		"authorization_id": a.AuthorizationID,
		"from_user_id":     a.FromUserID,
		"from_handle":      a.FromHandle,
		"to_user_id":       a.ToUserID,
		"to_handle":        a.ToHandle,
		"amount":           a.Amount,
		"captured_amount":  a.CapturedAmount,
		"remaining_amount": rem,
		"currency":         currency,
		"note":             a.Note,
		"visibility":       a.Visibility,
		"status":           a.Status,
		"expires_at":       a.ExpiresAt,
		"payment_id":       a.PaymentID,
		"payment_ids":      pids,
		"created_at":       a.CreatedAt,
		"closed_at":        a.ClosedAt,
	}
}

func (s *Store) marshalAuth(a Authorization) []byte {
	b, _ := json.Marshal(authResponse(a, s.Currency))
	return b
}

func openHoldForFixture(a fixtureAuthorization, nowT time.Time) (int64, error) {
	if a.Status != "open" {
		return 0, nil
	}
	exp, ok := parseTime(a.ExpiresAt)
	if !ok {
		return 0, errFixture("invalid authorization expires_at")
	}
	if !exp.After(nowT) {
		return 0, nil
	}
	cap := a.CapturedAmount
	if cap < 0 || cap > a.Amount {
		return 0, errFixture("invalid authorization captured amount")
	}
	return a.Amount - cap, nil
}

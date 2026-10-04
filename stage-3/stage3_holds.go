package main

import "time"

func (s *Store) authOpenAtLocked(a *Authorization, at time.Time) bool {
	createdT, ok := parseTime(a.CreatedAt)
	if !ok || createdT.After(at) {
		return false
	}
	switch a.Status {
	case "open":
		exp, ok := parseTime(a.ExpiresAt)
		if ok && !exp.After(at) {
			return false
		}
		return true
	case "voided", "captured", "expired":
		if a.ClosedAt == nil {
			return false
		}
		closedT, ok := parseTime(*a.ClosedAt)
		if !ok {
			return false
		}
		return closedT.After(at)
	default:
		return false
	}
}

func (s *Store) heldForUserAtLocked(userID string, at time.Time, knownAt *time.Time) int64 {
	var held int64
	for i := range s.Authorizations {
		a := &s.Authorizations[i]
		if a.FromUserID != userID {
			continue
		}
		if !s.authOpenAtLocked(a, at) {
			continue
		}
		rem := a.Amount - a.CapturedAmount
		if rem < 0 {
			rem = 0
		}
		held += rem
	}
	_ = knownAt
	return held
}

func (s *Store) setAuthClosedLocked(a *Authorization, when string) {
	a.ClosedAt = &when
}

func (s *Store) refreshAuthorizationExpiryLockedWithClose() {
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
			closed := mustFormatTime(exp)
			s.setAuthClosedLocked(a, closed)
		}
	}
}

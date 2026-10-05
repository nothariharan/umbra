package main

import (
	"sort"
	"time"
)

func (s *Store) findPaymentIndex(id string) int {
	for i := range s.Payments {
		if s.Payments[i].PaymentID == id {
			return i
		}
	}
	return -1
}

func (s *Store) paymentRevisionsLocked(pid string) []PaymentRevision {
	return s.PaymentRevisions[pid]
}

func (s *Store) latestRevisionLocked(pid string) (PaymentRevision, bool) {
	revs := s.PaymentRevisions[pid]
	if len(revs) == 0 {
		return PaymentRevision{}, false
	}
	return revs[len(revs)-1], true
}

func (s *Store) registerPaymentLocked(p Payment, applyBalance bool) {
	eff, rec := p.CreatedAt, p.CreatedAt
	if applyBalance {
		from := s.Users[p.FromUserID]
		to := s.Users[p.ToUserID]
		from.Balance -= p.Amount
		to.Balance += p.Amount
	}
	s.Payments = append(s.Payments, p)
	s.PaymentRevisions[p.PaymentID] = []PaymentRevision{{
		Revision: 1, Amount: p.Amount,
		EffectiveAt: eff, RecordedAt: rec,
		Reason: "",
	}}
	if p.SettlementID != nil || p.AuthorizationID != nil || p.RefundOf != nil {
		if s.ImmutablePayments == nil {
			s.ImmutablePayments = make(map[string]struct{})
		}
		s.ImmutablePayments[p.PaymentID] = struct{}{}
	}
}

func (s *Store) totalRefundedLocked(targetID string) int64 {
	var sum int64
	for _, p := range s.Payments {
		if p.RefundOf != nil && *p.RefundOf == targetID {
			sum += p.Amount
		}
	}
	return sum
}

func (s *Store) correctionAmountValidLocked(cur PaymentRevision, amount int64, pid string) bool {
	refunded := s.totalRefundedLocked(pid)
	if refunded == 0 {
		return true
	}
	if amount < refunded {
		return false
	}
	return amount >= cur.Amount-refunded
}

func (s *Store) settlementMembersLocked(settlementID string) []string {
	var ids []string
	for _, p := range s.Payments {
		if p.SettlementID != nil && *p.SettlementID == settlementID {
			ids = append(ids, p.PaymentID)
		}
	}
	return ids
}

func (s *Store) selectedRevisionAtLocked(pid string, knownAt *time.Time) (PaymentRevision, bool) {
	revs := s.PaymentRevisions[pid]
	if len(revs) == 0 {
		return PaymentRevision{}, false
	}
	if knownAt == nil {
		return revs[len(revs)-1], true
	}
	var sel *PaymentRevision
	for i := range revs {
		recT, ok := parseTime(revs[i].RecordedAt)
		if !ok || recT.After(*knownAt) {
			continue
		}
		if sel == nil || revs[i].Revision > sel.Revision {
			cp := revs[i]
			sel = &cp
		}
	}
	if sel == nil {
		return PaymentRevision{}, false
	}
	return *sel, true
}

func (s *Store) paymentVisibleAtKnownLocked(p Payment, knownAt *time.Time) bool {
	if knownAt == nil {
		return true
	}
	_, ok := s.selectedRevisionAtLocked(p.PaymentID, knownAt)
	return ok
}

func (s *Store) callerDeltaLocked(p Payment, rev PaymentRevision, userID string) int64 {
	if p.FromUserID == userID {
		return -rev.Amount
	}
	if p.ToUserID == userID {
		return rev.Amount
	}
	return 0
}

func paymentWithRevisionAmount(p Payment, rev PaymentRevision) Payment {
	out := p
	out.Amount = rev.Amount
	return out
}

type timelineEvent struct {
	effective time.Time
	pid       string
}

func (s *Store) collectTimelineEventsLocked(knownAt *time.Time, overridePID string, overrideRev *PaymentRevision) []timelineEvent {
	var events []timelineEvent
	for _, p := range s.Payments {
		var rev PaymentRevision
		var ok bool
		if overridePID != "" && p.PaymentID == overridePID && overrideRev != nil {
			rev = *overrideRev
			ok = true
		} else {
			rev, ok = s.selectedRevisionAtLocked(p.PaymentID, knownAt)
		}
		if !ok {
			continue
		}
		effT, ok2 := parseTime(rev.EffectiveAt)
		if !ok2 {
			continue
		}
		events = append(events, timelineEvent{effective: effT, pid: p.PaymentID})
	}
	sort.Slice(events, func(i, j int) bool {
		if events[i].effective.Equal(events[j].effective) {
			return events[i].pid < events[j].pid
		}
		return events[i].effective.Before(events[j].effective)
	})
	return events
}

func (s *Store) balanceStrictlyBeforeInstantLocked(userID string, at time.Time, knownAt *time.Time, overridePID string, overrideRev *PaymentRevision) int64 {
	bal := s.OpeningBalances[userID]
	events := s.collectTimelineEventsLocked(knownAt, overridePID, overrideRev)
	for _, ev := range events {
		if !ev.effective.Before(at) {
			break
		}
		idx := s.findPaymentIndex(ev.pid)
		if idx < 0 {
			continue
		}
		p := s.Payments[idx]
		var rev PaymentRevision
		var ok bool
		if overridePID != "" && p.PaymentID == overridePID && overrideRev != nil {
			rev = *overrideRev
			ok = true
		} else {
			rev, ok = s.selectedRevisionAtLocked(p.PaymentID, knownAt)
		}
		if !ok {
			continue
		}
		bal += s.callerDeltaLocked(p, rev, userID)
	}
	return bal
}

func (s *Store) balanceAtInstantLocked(userID string, at time.Time, knownAt *time.Time, overridePID string, overrideRev *PaymentRevision) int64 {
	bal := s.OpeningBalances[userID]
	events := s.collectTimelineEventsLocked(knownAt, overridePID, overrideRev)
	for _, ev := range events {
		if ev.effective.After(at) {
			break
		}
		idx := s.findPaymentIndex(ev.pid)
		if idx < 0 {
			continue
		}
		p := s.Payments[idx]
		var rev PaymentRevision
		var ok bool
		if overridePID != "" && p.PaymentID == overridePID && overrideRev != nil {
			rev = *overrideRev
			ok = true
		} else {
			rev, ok = s.selectedRevisionAtLocked(p.PaymentID, knownAt)
		}
		if !ok {
			continue
		}
		bal += s.callerDeltaLocked(p, rev, userID)
	}
	return bal
}

func (s *Store) checkHistoricalOverdraftForPaymentLocked(pid string, newRev PaymentRevision, knownAt *time.Time) bool {
	if s.findPaymentIndex(pid) < 0 {
		return false
	}
	oldRev, ok := s.latestRevisionLocked(pid)
	if !ok {
		return false
	}

	checkpoints := map[int64]struct{}{}
	for _, pay := range s.Payments {
		revs := s.PaymentRevisions[pay.PaymentID]
		for _, r := range revs {
			if t, ok := parseTime(r.EffectiveAt); ok {
				checkpoints[t.UnixNano()] = struct{}{}
			}
		}
	}
	if t, ok := parseTime(newRev.EffectiveAt); ok {
		checkpoints[t.UnixNano()] = struct{}{}
	}

	for ns := range checkpoints {
		at := time.Unix(0, ns)
		for uid := range s.Users {
			total := s.balanceAtInstantLocked(uid, at, knownAt, pid, &newRev)
			if total < 0 {
				return true
			}
			held := s.heldForUserAtLocked(uid, at, knownAt)
			if total-held < 0 {
				return true
			}
		}
	}
	_ = oldRev
	return false
}

type correctionApplyOpts struct {
	operatorBatch    bool
	allowSettlement  bool
	batchID          *string
	sharedRecordedAt string
}

func (s *Store) applyCorrectionLocked(pid string, u *User, expectedRev int, amount int64, effectiveAt, reason string, opts correctionApplyOpts) (PaymentRevision, int, string) {
	idx := s.findPaymentIndex(pid)
	if idx < 0 {
		return PaymentRevision{}, httpStatusNotFound, "not_found"
	}
	p := s.Payments[idx]
	if opts.operatorBatch {
		if _, op := s.SettlementOperators[u.ID]; !op {
			return PaymentRevision{}, httpStatusForbidden, "forbidden"
		}
	} else if p.FromUserID != u.ID {
		return PaymentRevision{}, httpStatusForbidden, "forbidden"
	}
	if p.RefundOf != nil || p.AuthorizationID != nil {
		return PaymentRevision{}, httpStatusUnprocessable, "linked_payment_immutable"
	}
	if p.SettlementID != nil && !opts.allowSettlement {
		return PaymentRevision{}, httpStatusUnprocessable, "linked_payment_immutable"
	}
	if !opts.allowSettlement {
		if _, imm := s.ImmutablePayments[pid]; imm {
			return PaymentRevision{}, httpStatusUnprocessable, "linked_payment_immutable"
		}
	}
	cur, ok := s.latestRevisionLocked(pid)
	if !ok || cur.Revision != expectedRev {
		return PaymentRevision{}, httpStatusConflict, "stale_revision"
	}
	effT, ok := parseTime(effectiveAt)
	if !ok {
		return PaymentRevision{}, httpStatusUnprocessable, "validation_failed"
	}
	if effT.After(now()) {
		return PaymentRevision{}, httpStatusUnprocessable, "validation_failed"
	}
	if !s.correctionAmountValidLocked(cur, amount, pid) {
		return PaymentRevision{}, httpStatusUnprocessable, "refund_exceeds_payment"
	}

	delta := amount - cur.Amount
	from := s.Users[p.FromUserID]
	to := s.Users[p.ToUserID]

	recorded := opts.sharedRecordedAt
	if recorded == "" {
		recorded = nowRFC3339()
	}
	lastT, hasLast := parseTime(cur.RecordedAt)
	curEffT, hasCurEff := parseTime(cur.EffectiveAt)
	if hasLast {
		if recT, ok2 := parseTime(recorded); ok2 && !recT.After(lastT) {
			recorded = mustFormatTime(lastT.Add(time.Second))
		}
		if hasCurEff && effT.Before(curEffT) {
			bump := lastT.Add(time.Second)
			nowT := now()
			if bump.After(nowT) {
				bump = nowT
			}
			if !bump.After(lastT) {
				bump = lastT.Add(time.Second)
			}
			recorded = mustFormatTime(bump)
		}
	}
	newRev := PaymentRevision{
		Revision: cur.Revision + 1, Amount: amount,
		EffectiveAt: effectiveAt, RecordedAt: recorded,
		Reason: reason, CorrectionBatchID: opts.batchID,
	}

	backdated := hasCurEff && effT.Before(curEffT)
	if backdated {
		if s.checkHistoricalOverdraftForPaymentLocked(pid, newRev, nil) {
			return PaymentRevision{}, httpStatusConflict, "historical_overdraft"
		}
	}
	if delta > 0 && s.availableForUserLocked(from.ID) < delta {
		return PaymentRevision{}, httpStatusConflict, "insufficient_funds"
	}
	if s.checkHistoricalOverdraftForPaymentLocked(pid, newRev, nil) {
		return PaymentRevision{}, httpStatusConflict, "historical_overdraft"
	}

	from.Balance -= delta
	to.Balance += delta
	s.PaymentRevisions[pid] = append(s.PaymentRevisions[pid], newRev)
	return newRev, httpStatusCreated, ""
}

const (
	httpStatusNotFound        = 404
	httpStatusForbidden       = 403
	httpStatusConflict        = 409
	httpStatusUnprocessable   = 422
	httpStatusCreated         = 201
)

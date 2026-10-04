package main

import (
	"crypto/rand"
	"encoding/hex"
	"sort"
	"time"
)

func newSnapshotToken() string {
	b := make([]byte, 24)
	_, _ = rand.Read(b)
	return "snap_" + hex.EncodeToString(b)
}

func (s *Store) hasAnyCorrectionLocked() bool {
	for _, revs := range s.PaymentRevisions {
		if len(revs) > 1 {
			return true
		}
	}
	return false
}

func (s *Store) buildStatementLocked(userID string, fromT, toT *time.Time, knownAtRaw string, knownAt *time.Time) statementSnapshot {
	legacy := knownAt == nil && !s.hasAnyCorrectionLocked()

	type item struct {
		p   Payment
		rev PaymentRevision
	}
	var items []item
	for _, p := range s.Payments {
		if p.FromUserID != userID && p.ToUserID != userID {
			continue
		}
		if !s.paymentVisibleAtKnownLocked(p, knownAt) {
			continue
		}
		rev, ok := s.selectedRevisionAtLocked(p.PaymentID, knownAt)
		if !ok {
			continue
		}
		sortTime, ok := parseTime(rev.EffectiveAt)
		if legacy {
			sortTime, ok = parseTime(p.CreatedAt)
		}
		if !ok {
			continue
		}
		if fromT != nil && sortTime.Before(*fromT) {
			continue
		}
		if toT != nil && !sortTime.Before(*toT) {
			continue
		}
		items = append(items, item{p: p, rev: rev})
	}
	sort.Slice(items, func(i, j int) bool {
		ti, _ := parseTime(items[i].rev.EffectiveAt)
		tj, _ := parseTime(items[j].rev.EffectiveAt)
		if legacy {
			ti, _ = parseTime(items[i].p.CreatedAt)
			tj, _ = parseTime(items[j].p.CreatedAt)
		}
		if ti.Equal(tj) {
			return items[i].p.PaymentID < items[j].p.PaymentID
		}
		return ti.Before(tj)
	})

	opening := s.OpeningBalances[userID]
	if fromT != nil {
		opening = s.balanceStrictlyBeforeInstantLocked(userID, *fromT, knownAt, "", nil)
	} else {
		opening = s.OpeningBalances[userID]
	}

	running := opening
	var entries []statementEntry
	for _, it := range items {
		delta := s.callerDeltaLocked(it.p, it.rev, userID)
		running += delta
		ent := statementEntry{
			Payment: paymentWithRevisionAmount(it.p, it.rev),
			Delta:   delta, BalanceAfter: running,
		}
		showMeta := !legacy || it.p.SettlementID != nil || it.p.AuthorizationID != nil
		if !legacy {
			showMeta = true
		}
		if showMeta {
			ent.Revision = it.rev.Revision
			ent.EffectiveAt = it.rev.EffectiveAt
			ent.RecordedAt = it.rev.RecordedAt
		}
		entries = append(entries, ent)
	}

	closing := running
	if toT != nil {
		closing = s.balanceStrictlyBeforeInstantLocked(userID, *toT, knownAt, "", nil)
	}

	fromStr, toStr := "", ""
	if fromT != nil {
		fromStr = mustFormatTime(*fromT)
	}
	if toT != nil {
		toStr = mustFormatTime(*toT)
	}

	return statementSnapshot{
		UserID: userID, ResetAt: s.ResetAt,
		OpeningBalance: opening, ClosingBalance: closing,
		From: fromStr, To: toStr, KnownAt: knownAtRaw,
		Entries: entries,
	}
}

func paginateStatementEntries(entries []statementEntry, limit, offset int) ([]statementEntry, bool) {
	hasMore := len(entries) > offset+limit
	if offset > len(entries) {
		return emptyJSONArray[statementEntry](), false
	}
	end := offset + limit
	if end > len(entries) {
		end = len(entries)
	}
	page := entries[offset:end]
	if page == nil {
		page = emptyJSONArray[statementEntry]()
	}
	return page, hasMore
}

func (s *Store) getStatementSnapshotLocked(token, userID string) (*statementSnapshot, bool) {
	snap, ok := s.StatementSnapshots[token]
	if !ok || snap.UserID != userID || snap.ResetAt != s.ResetAt {
		return nil, false
	}
	cp := *snap
	return &cp, true
}

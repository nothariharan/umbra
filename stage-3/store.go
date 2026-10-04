package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"sync"
	"time"
	"unicode/utf8"

	"golang.org/x/crypto/bcrypt"
)

type User struct {
	ID          string `json:"id"`
	Email       string `json:"email"`
	PasswordHash string `json:"password_hash"`
	DisplayName string `json:"display_name"`
	Handle      string `json:"handle"`
	Balance     int64  `json:"balance"`
}

type Payment struct {
	PaymentID        string  `json:"payment_id"`
	FromUserID       string  `json:"from_user_id"`
	FromHandle       string  `json:"from_handle"`
	ToUserID         string  `json:"to_user_id"`
	ToHandle         string  `json:"to_handle"`
	Amount           int64   `json:"amount"`
	Currency         string  `json:"currency"`
	Note             string  `json:"note"`
	Visibility       string  `json:"visibility"`
	RequestID        *string `json:"request_id"`
	AuthorizationID  *string `json:"authorization_id"`
	SettlementID     *string `json:"settlement_id,omitempty"`
	CreatedAt        string  `json:"created_at"`
}

type MoneyRequest struct {
	RequestID       string  `json:"request_id"`
	RequesterID     string  `json:"requester_id"`
	RequesterHandle string  `json:"requester_handle"`
	PayerID         string  `json:"payer_id"`
	PayerHandle     string  `json:"payer_handle"`
	Amount          int64   `json:"amount"`
	Currency        string  `json:"currency"`
	Note            string  `json:"note"`
	Status          string  `json:"status"`
	PaymentID       *string `json:"payment_id"`
	CreatedAt       string  `json:"created_at"`
}

type IdempotencyRecord struct {
	BodyHash   string `json:"body_hash"`
	StatusCode int    `json:"status_code"`
	Response   []byte `json:"response"`
	Failed4xx  bool   `json:"failed_4xx"`
}

type Store struct {
	mu sync.Mutex

	Currency                  string                        `json:"currency"`
	MinorUnits                int                           `json:"minor_units"`
	AuthorizationTTLSeconds   int                           `json:"authorization_ttl_seconds"`
	SeededTotal               int64                         `json:"seeded_total"`
	Users                     map[string]*User              `json:"users"`
	UsersByEmail              map[string]string             `json:"users_by_email"`
	UsersByHandle             map[string]string             `json:"users_by_handle"`
	Tokens                    map[string]string             `json:"tokens"`
	Payments                  []Payment                     `json:"payments"`
	Requests                  []MoneyRequest                `json:"requests"`
	Authorizations            []Authorization               `json:"authorizations"`
	SettlementOperators       map[string]struct{}           `json:"settlement_operators"`
	Idempotency               map[string]*IdempotencyRecord `json:"idempotency"`
	OpeningBalances           map[string]int64              `json:"opening_balances"`
	PaymentRevisions          map[string][]PaymentRevision  `json:"payment_revisions"`
	ImmutablePayments         map[string]struct{}           `json:"immutable_payments"`
	StatementSnapshots        map[string]*statementSnapshot `json:"-"`
	ResetAt                   string                        `json:"reset_at"`
	lastMonotonicTime         time.Time
	idempotencyInProgress     map[string]chan struct{}
}

func (s *Store) nextEventTimeRFC3339Locked() string {
	t := now()
	if !s.lastMonotonicTime.IsZero() && !t.After(s.lastMonotonicTime) {
		t = s.lastMonotonicTime.Add(time.Second)
	}
	s.lastMonotonicTime = t
	return formatTime(t)
}

func NewStore() *Store {
	return &Store{
		AuthorizationTTLSeconds: 600,
		Users:                 make(map[string]*User),
		UsersByEmail:          make(map[string]string),
		UsersByHandle:         make(map[string]string),
		Tokens:                make(map[string]string),
		SettlementOperators:   make(map[string]struct{}),
		Idempotency:             make(map[string]*IdempotencyRecord),
		OpeningBalances:         make(map[string]int64),
		PaymentRevisions:        make(map[string][]PaymentRevision),
		ImmutablePayments:       make(map[string]struct{}),
		StatementSnapshots:      make(map[string]*statementSnapshot),
		idempotencyInProgress:   make(map[string]chan struct{}),
	}
}

func (s *Store) exportState() map[string]any {
	s.mu.Lock()
	defer s.mu.Unlock()
	raw, _ := json.Marshal(s.snapshot())
	var m map[string]any
	_ = json.Unmarshal(raw, &m)
	return m
}

type storeSnapshot struct {
	Currency                string                        `json:"currency"`
	MinorUnits                int                           `json:"minor_units"`
	AuthorizationTTLSeconds   int                           `json:"authorization_ttl_seconds"`
	SeededTotal               int64                         `json:"seeded_total"`
	Users                     map[string]*User              `json:"users"`
	UsersByEmail              map[string]string             `json:"users_by_email"`
	UsersByHandle             map[string]string             `json:"users_by_handle"`
	Tokens                    map[string]string             `json:"tokens"`
	Payments                  []Payment                     `json:"payments"`
	Requests                  []MoneyRequest                `json:"requests"`
	Authorizations            []Authorization               `json:"authorizations"`
	SettlementOperators       map[string]struct{}           `json:"settlement_operators"`
	Idempotency               map[string]*IdempotencyRecord `json:"idempotency"`
	OpeningBalances           map[string]int64              `json:"opening_balances"`
	PaymentRevisions          map[string][]PaymentRevision  `json:"payment_revisions"`
	ImmutablePayments         map[string]struct{}           `json:"immutable_payments"`
	ResetAt                   string                        `json:"reset_at"`
}

func (s *Store) snapshot() storeSnapshot {
	return storeSnapshot{
		Currency:                s.Currency,
		MinorUnits:              s.MinorUnits,
		AuthorizationTTLSeconds: s.AuthorizationTTLSeconds,
		SeededTotal:             s.SeededTotal,
		Users:                   s.Users,
		UsersByEmail:            s.UsersByEmail,
		UsersByHandle:           s.UsersByHandle,
		Tokens:                  s.Tokens,
		Payments:                s.Payments,
		Requests:                s.Requests,
		Authorizations:          s.Authorizations,
		SettlementOperators:     s.SettlementOperators,
		Idempotency:             s.Idempotency,
		OpeningBalances:         s.OpeningBalances,
		PaymentRevisions:        s.PaymentRevisions,
		ImmutablePayments:       s.ImmutablePayments,
		ResetAt:                 s.ResetAt,
	}
}

func (s *Store) loadSnapshot(snap storeSnapshot) {
	s.Currency = snap.Currency
	s.MinorUnits = snap.MinorUnits
	if snap.AuthorizationTTLSeconds <= 0 {
		s.AuthorizationTTLSeconds = 600
	} else {
		s.AuthorizationTTLSeconds = snap.AuthorizationTTLSeconds
	}
	s.SeededTotal = snap.SeededTotal
	s.Users = snap.Users
	if s.Users == nil {
		s.Users = make(map[string]*User)
	}
	s.UsersByEmail = snap.UsersByEmail
	if s.UsersByEmail == nil {
		s.UsersByEmail = make(map[string]string)
	}
	s.UsersByHandle = snap.UsersByHandle
	if s.UsersByHandle == nil {
		s.UsersByHandle = make(map[string]string)
	}
	s.Tokens = snap.Tokens
	if s.Tokens == nil {
		s.Tokens = make(map[string]string)
	}
	s.Payments = snap.Payments
	s.Requests = snap.Requests
	s.Authorizations = snap.Authorizations
	if s.Authorizations == nil {
		s.Authorizations = nil
	}
	s.SettlementOperators = snap.SettlementOperators
	if s.SettlementOperators == nil {
		s.SettlementOperators = make(map[string]struct{})
	}
	s.Idempotency = snap.Idempotency
	if s.Idempotency == nil {
		s.Idempotency = make(map[string]*IdempotencyRecord)
	}
	s.idempotencyInProgress = make(map[string]chan struct{})
	s.OpeningBalances = snap.OpeningBalances
	if s.OpeningBalances == nil {
		s.OpeningBalances = make(map[string]int64)
	}
	s.PaymentRevisions = snap.PaymentRevisions
	if s.PaymentRevisions == nil {
		s.PaymentRevisions = make(map[string][]PaymentRevision)
	}
	s.ImmutablePayments = snap.ImmutablePayments
	if s.ImmutablePayments == nil {
		s.ImmutablePayments = make(map[string]struct{})
	}
	s.ResetAt = snap.ResetAt
	s.StatementSnapshots = make(map[string]*statementSnapshot)
}

func newToken() string {
	b := make([]byte, 32)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func newID(prefix string) string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return prefix + hex.EncodeToString(b)
}

func hashPassword(pw string) (string, error) {
	h, err := bcrypt.GenerateFromPassword([]byte(pw), bcrypt.DefaultCost)
	return string(h), err
}

func checkPassword(hash, pw string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(pw)) == nil
}

type fixtureUser struct {
	ID          string `json:"id"`
	Email       string `json:"email"`
	Password    string `json:"password"`
	DisplayName string `json:"display_name"`
	Handle      string `json:"handle"`
	Balance     int64  `json:"balance"`
}

type fixturePayment struct {
	ID              string  `json:"id"`
	PaymentID       string  `json:"payment_id"`
	FromUserID      string  `json:"from_user_id"`
	ToUserID        string  `json:"to_user_id"`
	Amount          int64   `json:"amount"`
	Note            string  `json:"note"`
	Visibility      string  `json:"visibility"`
	CreatedAt       *string `json:"created_at"`
	SettlementID    *string `json:"settlement_id"`
	AuthorizationID *string `json:"authorization_id"`
}

type fixtureRequest struct {
	ID            string `json:"id"`
	RequestID     string `json:"request_id"`
	RequesterID   string `json:"requester_id"`
	PayerID       string `json:"payer_id"`
	Amount        int64  `json:"amount"`
	Note          string `json:"note"`
	Status        string `json:"status"`
}

type fixtureAuthorization struct {
	ID                string `json:"id"`
	AuthorizationID   string `json:"authorization_id"`
	FromUserID        string `json:"from_user_id"`
	ToUserID       string `json:"to_user_id"`
	Amount         int64  `json:"amount"`
	Note           string `json:"note"`
	Visibility     string `json:"visibility"`
	Status         string `json:"status"`
	ExpiresAt      string `json:"expires_at"`
	CapturedAmount int64  `json:"captured_amount"`
}

type fixture struct {
	Currency                  string                 `json:"currency"`
	MinorUnits                int                    `json:"minor_units"`
	AuthorizationTTLSeconds   *int                   `json:"authorization_ttl_seconds"`
	Users                     []fixtureUser          `json:"users"`
	Payments                  []fixturePayment       `json:"payments"`
	Requests                  []fixtureRequest       `json:"requests"`
	Authorizations            []fixtureAuthorization `json:"authorizations"`
	SettlementOperatorIDs     []string               `json:"settlement_operator_ids"`
}

func (s *Store) applyFixture(f fixture) error {
	if f.Currency == "" {
		return errFixture("currency required")
	}
	if f.MinorUnits != 0 && f.MinorUnits != 2 && f.MinorUnits != 3 {
		return errFixture("invalid minor_units")
	}
	if len(f.Users) == 0 {
		return errFixture("users required")
	}
	handles := map[string]struct{}{}
	emails := map[string]struct{}{}
	var total int64
	users := map[string]*User{}
	byEmail := map[string]string{}
	byHandle := map[string]string{}

	for _, u := range f.Users {
		if u.ID == "" || len(u.ID) > 64 {
			return errFixture("invalid user id")
		}
		if !validHandle(u.Handle) {
			return errFixture("invalid handle")
		}
		if _, ok := handles[u.Handle]; ok {
			return errFixture("duplicate handle")
		}
		handles[u.Handle] = struct{}{}
		if !validEmail(u.Email) {
			return errFixture("invalid email")
		}
		if _, ok := emails[u.Email]; ok {
			return errFixture("duplicate email")
		}
		emails[u.Email] = struct{}{}
		if u.Balance < 0 {
			return errFixture("negative balance")
		}
		total += u.Balance
		ph, err := hashPassword(u.Password)
		if err != nil {
			return err
		}
		users[u.ID] = &User{
			ID: u.ID, Email: u.Email, PasswordHash: ph,
			DisplayName: u.DisplayName, Handle: u.Handle, Balance: u.Balance,
		}
		byEmail[u.Email] = u.ID
		byHandle[u.Handle] = u.ID
	}

	nowT := now()
	for _, p := range f.Payments {
		if _, ok := users[p.FromUserID]; !ok {
			return errFixture("unknown payment user")
		}
		if _, ok := users[p.ToUserID]; !ok {
			return errFixture("unknown payment user")
		}
		if p.Amount < 0 || p.Amount > maxAmount {
			return errFixture("invalid payment amount")
		}
		if p.Visibility != "public" && p.Visibility != "private" {
			return errFixture("invalid visibility")
		}
		if p.CreatedAt != nil {
			if *p.CreatedAt == "" {
				return errFixture("invalid payment created_at")
			}
			ct, ok := parseTime(*p.CreatedAt)
			if !ok {
				return errFixture("invalid payment created_at")
			}
			if ct.After(nowT) {
				return errFixture("future payment created_at")
			}
		}
	}

	for _, r := range f.Requests {
		if _, ok := users[r.RequesterID]; !ok {
			return errFixture("unknown request user")
		}
		if _, ok := users[r.PayerID]; !ok {
			return errFixture("unknown request user")
		}
		if r.Amount < 0 || r.Amount > maxAmount {
			return errFixture("invalid request amount")
		}
		switch r.Status {
		case "pending", "paid", "declined", "cancelled":
		default:
			return errFixture("invalid request status")
		}
	}

	ops := map[string]struct{}{}
	for _, id := range f.SettlementOperatorIDs {
		if _, ok := users[id]; !ok {
			return errFixture("unknown operator")
		}
		ops[id] = struct{}{}
	}

	ttl := 600
	if f.AuthorizationTTLSeconds != nil {
		if *f.AuthorizationTTLSeconds <= 0 {
			return errFixture("invalid authorization_ttl_seconds")
		}
		ttl = *f.AuthorizationTTLSeconds
	}

	heldByUser := map[string]int64{}
	for _, a := range f.Authorizations {
		if _, ok := users[a.FromUserID]; !ok {
			return errFixture("unknown authorization user")
		}
		if _, ok := users[a.ToUserID]; !ok {
			return errFixture("unknown authorization user")
		}
		if a.Amount < 1 || a.Amount > maxAmount {
			return errFixture("invalid authorization amount")
		}
		if a.Visibility != "" && a.Visibility != "public" && a.Visibility != "private" {
			return errFixture("invalid authorization visibility")
		}
		if utf8.RuneCountInString(a.Note) > maxNoteRunes {
			return errFixture("invalid authorization note")
		}
		switch a.Status {
		case "open", "captured", "voided", "expired":
		default:
			return errFixture("invalid authorization status")
		}
		if a.Status == "open" {
			if _, ok := parseTime(a.ExpiresAt); !ok {
				return errFixture("invalid authorization expires_at")
			}
		}
		cap := a.CapturedAmount
		if cap < 0 || cap > a.Amount {
			return errFixture("invalid authorization captured amount")
		}
		if a.Status == "captured" && cap == 0 {
			cap = a.Amount
		}
		hold, err := openHoldForFixture(fixtureAuthorization{
			ID: a.ID, FromUserID: a.FromUserID, ToUserID: a.ToUserID,
			Amount: a.Amount, Status: a.Status, ExpiresAt: a.ExpiresAt,
			CapturedAmount: cap,
		}, nowT)
		if err != nil {
			return err
		}
		heldByUser[a.FromUserID] += hold
	}
	for uid, held := range heldByUser {
		if held > users[uid].Balance {
			return errFixture("authorization holds exceed balance")
		}
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	s.Currency = f.Currency
	s.MinorUnits = f.MinorUnits
	s.AuthorizationTTLSeconds = ttl
	s.SeededTotal = total
	s.Users = users
	s.UsersByEmail = byEmail
	s.UsersByHandle = byHandle
	prevTokens := s.Tokens
	s.Tokens = make(map[string]string)
	for tok, uid := range prevTokens {
		if users[uid] != nil {
			s.Tokens[tok] = uid
		}
	}
	s.Idempotency = make(map[string]*IdempotencyRecord)
	s.idempotencyInProgress = make(map[string]chan struct{})
	s.SettlementOperators = ops
	s.Payments = nil
	s.Requests = nil
	s.Authorizations = nil
	s.PaymentRevisions = make(map[string][]PaymentRevision)
	s.ImmutablePayments = make(map[string]struct{})
	s.StatementSnapshots = make(map[string]*statementSnapshot)
	s.OpeningBalances = make(map[string]int64)
	for uid, u := range users {
		s.OpeningBalances[uid] = u.Balance
	}

	resetAt := nowRFC3339()
	s.ResetAt = resetAt
	if rt, ok := parseTime(resetAt); ok {
		s.lastMonotonicTime = rt
	}
	netOriginal := map[string]int64{}
	for _, p := range f.Payments {
		netOriginal[p.FromUserID] -= p.Amount
		netOriginal[p.ToUserID] += p.Amount
	}
	for uid, delta := range netOriginal {
		s.OpeningBalances[uid] -= delta
	}

	for _, p := range f.Payments {
		from := users[p.FromUserID]
		to := users[p.ToUserID]
		pid := p.PaymentID
		if pid == "" {
			pid = p.ID
		}
		if pid == "" {
			pid = newID("p_")
		}
		created := resetAt
		if p.CreatedAt != nil {
			created = *p.CreatedAt
		}
		pay := Payment{
			PaymentID: pid, FromUserID: from.ID, FromHandle: from.Handle,
			ToUserID: to.ID, ToHandle: to.Handle, Amount: p.Amount,
			Currency: f.Currency, Note: p.Note, Visibility: p.Visibility,
			RequestID: nil, AuthorizationID: p.AuthorizationID, SettlementID: p.SettlementID,
			CreatedAt: created,
		}
		s.registerPaymentLocked(pay, false)
	}

	for _, r := range f.Requests {
		reqr := users[r.RequesterID]
		payer := users[r.PayerID]
		rid := r.RequestID
		if rid == "" {
			rid = r.ID
		}
		if rid == "" {
			rid = newID("rq_")
		}
		mr := MoneyRequest{
			RequestID: rid, RequesterID: reqr.ID, RequesterHandle: reqr.Handle,
			PayerID: payer.ID, PayerHandle: payer.Handle, Amount: r.Amount,
			Currency: f.Currency, Note: r.Note, Status: r.Status,
			PaymentID: nil, CreatedAt: resetAt,
		}
		s.Requests = append(s.Requests, mr)
	}

	for _, a := range f.Authorizations {
		from := users[a.FromUserID]
		to := users[a.ToUserID]
		aid := a.AuthorizationID
		if aid == "" {
			aid = a.ID
		}
		if aid == "" {
			aid = newID("a_")
		}
		vis := a.Visibility
		if vis == "" {
			vis = "public"
		}
		capAmt := a.CapturedAmount
		if a.Status == "captured" && capAmt == 0 {
			capAmt = a.Amount
		}
		st := a.Status
		exp := a.ExpiresAt
		if st == "open" {
			expT, _ := parseTime(exp)
			if !expT.After(nowT) {
				st = "expired"
			}
		}
		s.Authorizations = append(s.Authorizations, Authorization{
			AuthorizationID: aid, FromUserID: from.ID, FromHandle: from.Handle,
			ToUserID: to.ID, ToHandle: to.Handle, Amount: a.Amount,
			CapturedAmount: capAmt, Note: a.Note, Visibility: vis, Status: st,
			ExpiresAt: exp, CreatedAt: resetAt, PaymentID: nil, PaymentIDs: []string{},
		})
	}

	return nil
}

type fixtureError struct{ msg string }

func (e fixtureError) Error() string { return e.msg }
func errFixture(msg string) error   { return fixtureError{msg: msg} }

func (s *Store) userByToken(token string) (*User, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	uid, ok := s.Tokens[token]
	if !ok {
		return nil, false
	}
	u, ok := s.Users[uid]
	return u, ok
}

func (s *Store) getUser(id string) *User {
	return s.Users[id]
}

func splitShares(amount int64, n int) []int64 {
	if n <= 0 {
		return nil
	}
	base := amount / int64(n)
	rem := amount % int64(n)
	out := make([]int64, n)
	for i := 0; i < n; i++ {
		out[i] = base
		if int64(i) < rem {
			out[i]++
		}
	}
	return out
}

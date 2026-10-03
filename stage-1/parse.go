package main

import (
	"encoding/json"
	"math"
	"net/mail"
	"regexp"
	"strconv"
	"strings"
	"unicode/utf8"
)

const maxAmount int64 = 1000000000

var handleRe = regexp.MustCompile(`^[a-z0-9_]{1,20}$`)

func parseIntegralAmount(raw json.RawMessage) (int64, bool, errorKind) {
	if len(raw) == 0 {
		return 0, false, errValidation
	}
	var v any
	if err := json.Unmarshal(raw, &v); err != nil {
		return 0, false, errMalformed
	}
	switch x := v.(type) {
	case string, bool:
		return 0, false, errValidation
	case float64:
		if math.IsNaN(x) || math.IsInf(x, 0) {
			return 0, false, errValidation
		}
		if x != math.Trunc(x) {
			return 0, false, errValidation
		}
		if x <= 0 || x > float64(maxAmount) {
			return 0, false, errValidation
		}
		return int64(x), true, errNone
	default:
		return 0, false, errMalformed
	}
}

type errorKind int

const (
	errNone errorKind = iota
	errMalformed
	errValidation
)

func parseQueryInt(s string, def *int) (int, errorKind) {
	if s == "" {
		if def != nil {
			return *def, errNone
		}
		return 0, errValidation
	}
	if len(s) > 1 && s[0] == '+' {
		return 0, errValidation
	}
	for _, r := range s {
		if r < '0' || r > '9' {
			return 0, errValidation
		}
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0, errValidation
	}
	return n, errNone
}

func parseLimitOffset(q map[string][]string) (limit, offset int, ok bool) {
	defLimit := 20
	lim, ek := parseQueryInt(first(q["limit"]), &defLimit)
	if ek != errNone {
		return 0, 0, false
	}
	off, ek := parseQueryInt(first(q["offset"]), ptr(0))
	if ek != errNone {
		return 0, 0, false
	}
	if lim < 1 || lim > 200 || off < 0 {
		return 0, 0, false
	}
	return lim, off, true
}

func first(ss []string) string {
	if len(ss) == 0 {
		return ""
	}
	return ss[0]
}

func ptr(n int) *int { return &n }

func validEmail(email string) bool {
	if email == "" || utf8.RuneCountInString(email) > 254 {
		return false
	}
	addr, err := mail.ParseAddress(email)
	if err != nil {
		return false
	}
	parts := strings.SplitN(addr.Address, "@", 2)
	return len(parts) == 2 && parts[0] != "" && parts[1] != ""
}

func deriveHandle(email string) string {
	local := strings.SplitN(email, "@", 2)[0]
	local = strings.ToLower(local)
	var b strings.Builder
	for _, r := range local {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '_' {
			b.WriteRune(r)
		} else {
			b.WriteRune('_')
		}
	}
	s := b.String()
	if len(s) > 20 {
		s = s[:20]
	}
	if s == "" {
		s = "_"
	}
	return s
}

func validHandle(h string) bool {
	return handleRe.MatchString(h)
}

const maxNoteRunes = 200

func parseNoteField(body map[string]json.RawMessage, key string) (string, errorKind) {
	raw, ok := body[key]
	if !ok {
		return "", errNone
	}
	if string(raw) == "null" {
		return "", errValidation
	}
	var s string
	if err := json.Unmarshal(raw, &s); err != nil {
		return "", errValidation
	}
	if utf8.RuneCountInString(s) > maxNoteRunes {
		return "", errValidation
	}
	return s, errNone
}

func nowRFC3339() string {
	return mustFormatTime(now())
}

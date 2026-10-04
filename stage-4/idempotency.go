package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
)

func canonicalBodyHash(raw []byte) string {
	if len(raw) == 0 {
		h := sha256.Sum256(raw)
		return hex.EncodeToString(h[:])
	}
	var v any
	if err := json.Unmarshal(raw, &v); err != nil {
		h := sha256.Sum256(raw)
		return hex.EncodeToString(h[:])
	}
	canon, err := json.Marshal(v)
	if err != nil {
		h := sha256.Sum256(raw)
		return hex.EncodeToString(h[:])
	}
	h := sha256.Sum256(canon)
	return hex.EncodeToString(h[:])
}

func idempotencyKey(userID, method, path, key string) string {
	return userID + "\x00" + method + "\x00" + path + "\x00" + key
}

type idemResult struct {
	status int
	body   []byte
	replay bool
}

func (s *Store) beginIdempotency(fullKey, bodyHash string) (idemResult, func(int, []byte, bool), func(), bool) {
	s.mu.Lock()
	rec, ok := s.Idempotency[fullKey]
	if ok {
		if rec.Failed4xx {
			delete(s.Idempotency, fullKey)
		} else if rec.BodyHash != bodyHash {
			s.mu.Unlock()
			return idemResult{}, nil, nil, false
		} else {
			st := rec.StatusCode
			if st == 201 {
				st = 200
			}
			body := rec.Response
			s.mu.Unlock()
			return idemResult{status: st, body: body, replay: true}, nil, nil, true
		}
	}
	if ch, busy := s.idempotencyInProgress[fullKey]; busy {
		s.mu.Unlock()
		<-ch
		s.mu.Lock()
		rec2 := s.Idempotency[fullKey]
		if rec2 == nil {
			s.mu.Unlock()
			return idemResult{}, nil, nil, false
		}
		if rec2.Failed4xx {
			if rec2.BodyHash != bodyHash {
				delete(s.Idempotency, fullKey)
				s.mu.Unlock()
				return idemResult{}, nil, nil, false
			}
			st := rec2.StatusCode
			body := rec2.Response
			s.mu.Unlock()
			return idemResult{status: st, body: body, replay: true}, nil, nil, true
		}
		if rec2.BodyHash != bodyHash {
			s.mu.Unlock()
			return idemResult{}, nil, nil, false
		}
		st := rec2.StatusCode
		if st == 201 {
			st = 200
		}
		body := rec2.Response
		s.mu.Unlock()
		return idemResult{status: st, body: body, replay: true}, nil, nil, true
	}
	ch := make(chan struct{})
	s.idempotencyInProgress[fullKey] = ch
	s.mu.Unlock()

	commit := func(status int, body []byte, failed4xx bool) {
		s.mu.Lock()
		delete(s.idempotencyInProgress, fullKey)
		if failed4xx {
			s.Idempotency[fullKey] = &IdempotencyRecord{
				BodyHash: bodyHash, StatusCode: status, Response: body, Failed4xx: true,
			}
		} else {
			s.Idempotency[fullKey] = &IdempotencyRecord{
				BodyHash: bodyHash, StatusCode: status, Response: body, Failed4xx: false,
			}
		}
		close(ch)
		s.mu.Unlock()
	}
	abort := func() {
		s.mu.Lock()
		if ch, ok := s.idempotencyInProgress[fullKey]; ok {
			delete(s.idempotencyInProgress, fullKey)
			close(ch)
		}
		s.mu.Unlock()
	}
	return idemResult{}, commit, abort, true
}

func checkIdempotencyHeader(w http.ResponseWriter, r *http.Request) (string, bool) {
	key := r.Header.Get("Idempotency-Key")
	if key == "" {
		writeError(w, http.StatusBadRequest, "missing_idempotency_key", "Idempotency-Key required")
		return "", false
	}
	if len(key) > 255 {
		writeError(w, http.StatusUnprocessableEntity, "validation_failed", "invalid idempotency key")
		return "", false
	}
	return key, true
}

func writeIdemBody(w http.ResponseWriter, status int, body []byte) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_, _ = w.Write(body)
}

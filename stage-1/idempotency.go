package main

import (
	"crypto/sha256"
	"encoding/hex"
	"net/http"
)

func canonicalBodyHash(raw []byte) string {
	h := sha256.Sum256(raw)
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

func (s *Store) beginIdempotency(fullKey, bodyHash string) (idemResult, func(int, []byte, bool), bool) {
	s.mu.Lock()
	rec, ok := s.Idempotency[fullKey]
	if ok {
		if rec.BodyHash != bodyHash {
			s.mu.Unlock()
			return idemResult{}, nil, false
		}
		if rec.Failed4xx {
			delete(s.Idempotency, fullKey)
		} else {
			st := rec.StatusCode
			if st == 201 {
				st = 200
			}
			body := rec.Response
			s.mu.Unlock()
			return idemResult{status: st, body: body, replay: true}, nil, true
		}
	}
	if ch, busy := s.idempotencyInProgress[fullKey]; busy {
		s.mu.Unlock()
		<-ch
		s.mu.Lock()
		rec2 := s.Idempotency[fullKey]
		if rec2 == nil || rec2.BodyHash != bodyHash {
			s.mu.Unlock()
			return idemResult{}, nil, false
		}
		st := rec2.StatusCode
		if st == 201 {
			st = 200
		}
		body := rec2.Response
		s.mu.Unlock()
		return idemResult{status: st, body: body, replay: true}, nil, true
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
	return idemResult{}, commit, true
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

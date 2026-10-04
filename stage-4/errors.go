package main

import (
	"encoding/json"
	"net/http"
)

type apiError struct {
	Error struct {
		Code    string `json:"code"`
		Message string `json:"message"`
	} `json:"error"`
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	e := apiError{}
	e.Error.Code = code
	e.Error.Message = message
	_ = json.NewEncoder(w).Encode(e)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func emptyJSONArray[T any]() []T { return make([]T, 0) }

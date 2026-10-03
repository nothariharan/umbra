package main

import (
	"log"
	"net/http"
	"os"
	"strings"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	sv := &Server{store: NewStore()}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", sv.handleHealth)
	mux.HandleFunc("POST /_test/reset", sv.handleReset)
	mux.HandleFunc("GET /_test/export", sv.handleExport)
	mux.HandleFunc("POST /_test/import", sv.handleImport)
	mux.HandleFunc("POST /auth/signup", sv.handleSignup)
	mux.HandleFunc("POST /auth/login", sv.handleLogin)
	mux.HandleFunc("GET /me", sv.withAuth(sv.handleMe))
	mux.HandleFunc("POST /payments", sv.withAuth(sv.handlePayments))
	mux.HandleFunc("POST /requests", sv.withAuth(sv.handleCreateRequest))
	mux.HandleFunc("GET /requests", sv.withAuth(sv.handleListRequests))
	mux.HandleFunc("POST /splits", sv.withAuth(sv.handleSplits))
	mux.HandleFunc("GET /activity", sv.withAuth(sv.handleActivity))
	mux.HandleFunc("POST /settlements", sv.withAuth(sv.handleSettlements))
	mux.HandleFunc("POST /requests/{id}/pay", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		sv.withAuth(func(w http.ResponseWriter, r *http.Request) {
			sv.handlePayRequest(w, r, id)
		})(w, r)
	})
	mux.HandleFunc("POST /requests/{id}/decline", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		sv.withAuth(func(w http.ResponseWriter, r *http.Request) {
			sv.handleDeclineRequest(w, r, id)
		})(w, r)
	})
	mux.HandleFunc("POST /requests/{id}/cancel", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		sv.withAuth(func(w http.ResponseWriter, r *http.Request) {
			sv.handleCancelRequest(w, r, id)
		})(w, r)
	})

	addr := "0.0.0.0:" + port
	log.Printf("listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatal(err)
	}
}

func (sv *Server) withAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" || strings.HasPrefix(r.URL.Path, "/_test/") ||
			r.URL.Path == "/auth/signup" || r.URL.Path == "/auth/login" {
			next(w, r)
			return
		}
		if _, ok := sv.authUser(r); !ok {
			writeError(w, http.StatusUnauthorized, "unauthenticated", "authentication required")
			return
		}
		next(w, r)
	}
}

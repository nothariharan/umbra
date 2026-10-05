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
	seedDemoAccounts(sv)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", sv.handleHealth)
	mux.HandleFunc("POST /_test/reset", sv.handleReset)
	mux.HandleFunc("GET /_test/export", sv.handleExport)
	mux.HandleFunc("POST /_test/import", sv.handleImport)
	mux.HandleFunc("POST /auth/signup", sv.handleSignup)
	mux.HandleFunc("POST /auth/login", sv.handleLogin)
	mux.HandleFunc("GET /me", sv.withAuth(sv.handleMe))
	mux.HandleFunc("GET /statement", sv.withAuth(sv.handleStatement))
	mux.HandleFunc("POST /payments", sv.withAuth(sv.handlePayments))
	mux.HandleFunc("GET /payments/{id}/revisions", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		sv.withAuth(func(w http.ResponseWriter, r *http.Request) {
			sv.handlePaymentRevisions(w, r, id)
		})(w, r)
	})
	mux.HandleFunc("POST /payments/{id}/corrections", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		sv.withAuth(func(w http.ResponseWriter, r *http.Request) {
			sv.handlePaymentCorrection(w, r, id)
		})(w, r)
	})
	mux.HandleFunc("POST /payments/{id}/refunds", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		sv.withAuth(func(w http.ResponseWriter, r *http.Request) {
			sv.handlePaymentRefund(w, r, id)
		})(w, r)
	})
	mux.HandleFunc("POST /correction-batches", sv.withAuth(sv.handleCorrectionBatch))
	mux.HandleFunc("POST /requests", sv.withAuth(sv.handleCreateRequest))
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
	mux.HandleFunc("POST /authorizations", sv.withAuth(sv.handleCreateAuthorization))
	mux.HandleFunc("GET /authorizations", sv.handleAuthorizationsRoute)
	mux.HandleFunc("POST /authorizations/{id}/capture", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		sv.withAuth(func(w http.ResponseWriter, r *http.Request) {
			sv.handleCaptureAuthorization(w, r, id)
		})(w, r)
	})
	mux.HandleFunc("POST /authorizations/{id}/void", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		sv.withAuth(func(w http.ResponseWriter, r *http.Request) {
			sv.handleVoidAuthorization(w, r, id)
		})(w, r)
	})

	mux.HandleFunc("GET /", sv.handleHome)
	mux.HandleFunc("GET /signup", sv.handleSignupPage)
	mux.HandleFunc("GET /login", sv.handleLoginPage)
	mux.HandleFunc("GET /split", sv.handleSplitPage)
	mux.HandleFunc("GET /requests", sv.handleRequestsRoute)
	mux.Handle("GET /static/", http.StripPrefix("/static/", http.FileServer(http.FS(staticFiles))))

	addr := "0.0.0.0:" + port
	log.Printf("listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatal(err)
	}
}

func (sv *Server) withAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" || strings.HasPrefix(r.URL.Path, "/_test/") ||
			strings.HasPrefix(r.URL.Path, "/static/") ||
			r.URL.Path == "/auth/signup" || r.URL.Path == "/auth/login" ||
			r.URL.Path == "/" || r.URL.Path == "/signup" || r.URL.Path == "/login" {
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

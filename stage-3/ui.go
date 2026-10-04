package main

import (
	"embed"
	"io/fs"
	"net/http"
	"strconv"
	"strings"
)

//go:embed web/*
var webRoot embed.FS

var staticFiles fs.FS

func init() {
	sub, err := fs.Sub(webRoot, "web/static")
	if err != nil {
		panic(err)
	}
	staticFiles = sub
}

func wantsHTML(r *http.Request) bool {
	accept := r.Header.Get("Accept")
	if !strings.Contains(accept, "text/html") {
		return false
	}
	bestHTML, bestJSON := 0.0, -1.0
	hasHTML := false
	for _, part := range strings.Split(accept, ",") {
		part = strings.TrimSpace(part)
		media := part
		q := 1.0
		if i := strings.Index(part, ";"); i >= 0 {
			media = strings.TrimSpace(part[:i])
			for _, param := range strings.Split(part[i+1:], ";") {
				param = strings.TrimSpace(param)
				if strings.HasPrefix(param, "q=") {
					if v, err := strconv.ParseFloat(strings.TrimPrefix(param, "q="), 64); err == nil {
						q = v
					}
				}
			}
		}
		if media == "text/html" {
			hasHTML = true
			if q > bestHTML {
				bestHTML = q
			}
		}
		if media == "application/json" && q > bestJSON {
			bestJSON = q
		}
	}
	if !hasHTML {
		return false
	}
	if bestJSON < 0 {
		return true
	}
	return bestHTML > bestJSON
}

func (sv *Server) servePage(w http.ResponseWriter, name string) {
	b, err := webRoot.ReadFile("web/" + name)
	if err != nil {
		http.NotFound(w, nil)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(b)
}

func (sv *Server) handleHome(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	sv.servePage(w, "index.html")
}

func (sv *Server) handleSignupPage(w http.ResponseWriter, r *http.Request) {
	sv.servePage(w, "signup.html")
}

func (sv *Server) handleLoginPage(w http.ResponseWriter, r *http.Request) {
	sv.servePage(w, "login.html")
}

func (sv *Server) handleSplitPage(w http.ResponseWriter, r *http.Request) {
	sv.servePage(w, "split.html")
}

func (sv *Server) handleRequestsRoute(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if wantsHTML(r) {
		sv.servePage(w, "requests.html")
		return
	}
	sv.withAuth(sv.handleListRequests)(w, r)
}

func (sv *Server) handleAuthorizationsRoute(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if wantsHTML(r) {
		sv.servePage(w, "authorizations.html")
		return
	}
	sv.withAuth(sv.handleListAuthorizations)(w, r)
}

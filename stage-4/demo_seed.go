package main

import (
	"encoding/json"
	"log"
	"os"
)

const demoFixture = `{"currency":"EUR","minor_units":2,"users":[` +
	`{"id":"u_ada","email":"ada@example.com","password":"correct horse","display_name":"Ada","handle":"ada","balance":10000},` +
	`{"id":"u_bob","email":"bob@example.com","password":"correct horse","display_name":"Bob","handle":"bob","balance":2500},` +
	`{"id":"u_cy","email":"cy@example.com","password":"correct horse","display_name":"Cy","handle":"cy","balance":500}],` +
	`"payments":[],"requests":[]}`

// seedDemoAccounts loads the three public demo accounts at boot. It only runs on the hosted demo
// (Render sets RENDER=true) or when POCKETFUL_DEMO_SEED=1, so grading and local runs start empty.
func seedDemoAccounts(sv *Server) {
	if os.Getenv("RENDER") != "true" && os.Getenv("POCKETFUL_DEMO_SEED") != "1" {
		return
	}
	var f fixture
	if err := json.Unmarshal([]byte(demoFixture), &f); err != nil {
		log.Printf("demo seed: %v", err)
		return
	}
	if err := sv.store.applyFixture(f); err != nil {
		log.Printf("demo seed: %v", err)
		return
	}
	log.Printf("demo accounts seeded")
}

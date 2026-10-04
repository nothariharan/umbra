package main

type PaymentRevision struct {
	Revision    int    `json:"revision"`
	Amount      int64  `json:"amount"`
	EffectiveAt string `json:"effective_at"`
	RecordedAt  string `json:"recorded_at"`
	Reason      string `json:"reason"`
}

type statementEntry struct {
	Payment      Payment `json:"payment"`
	Delta        int64   `json:"delta"`
	BalanceAfter int64   `json:"balance_after"`
	Revision     int     `json:"revision,omitempty"`
	EffectiveAt  string  `json:"effective_at,omitempty"`
	RecordedAt   string  `json:"recorded_at,omitempty"`
}

type statementSnapshot struct {
	Token          string
	UserID         string
	ResetAt        string
	OpeningBalance int64
	ClosingBalance int64
	From           string
	To             string
	KnownAt        string
	Entries        []statementEntry
}

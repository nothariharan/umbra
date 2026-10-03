package main

import "testing"

func TestSplitShares(t *testing.T) {
	sh := splitShares(100, 3)
	var sum int64
	for i, v := range sh {
		if i > 0 && sh[i-1]-sh[i] > 1 {
			t.Fatalf("shares differ by more than 1: %v", sh)
		}
		sum += v
	}
	if sum != 100 {
		t.Fatalf("sum=%d want 100", sum)
	}
	if len(sh) != 3 || sh[0] != 34 {
		t.Fatalf("got %v", sh)
	}
}

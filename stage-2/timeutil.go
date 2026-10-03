package main

import (
	"time"
)

var clock = func() time.Time { return time.Now().UTC() }

func now() time.Time { return clock() }

func formatTime(t time.Time) string {
	return t.Format("2006-01-02T15:04:05-07:00")
}

func mustFormatTime(t time.Time) string {
	return formatTime(t)
}

func parseTime(s string) (time.Time, bool) {
	t, err := time.Parse(time.RFC3339, s)
	if err != nil {
		return time.Time{}, false
	}
	return t, true
}

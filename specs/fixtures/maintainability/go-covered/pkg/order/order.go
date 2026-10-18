// Copyright (c) 2026 The Order Authors All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package order

import "fmt"

// Load reads an order by id.
func Load(id string) (string, error) {
	if id == "" {
		return "", fmt.Errorf("order id is required")
	}
	// return the id
	return id, nil
}

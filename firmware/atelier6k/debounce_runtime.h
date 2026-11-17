// Copyright 2026 thuanc177
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <stdint.h>

// Debounce time that can be changed while the keyboard is running.
// 0 disables debouncing; values above the maximum are clamped.
#define ATELIER_DEBOUNCE_DEFAULT 5
#define ATELIER_DEBOUNCE_MAX 25

void    atelier_debounce_set(uint8_t ms);
uint8_t atelier_debounce_get(void);

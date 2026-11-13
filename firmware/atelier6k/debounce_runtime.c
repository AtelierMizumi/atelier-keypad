// Copyright 2026 thuanc177
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Per-key asymmetric debounce whose time can be changed while the keyboard is
// running. Adapted from QMK's quantum/debounce/asym_eager_defer_pk.c, where
// the time is the compile-time constant DEBOUNCE.
//
// With D = the configured time in milliseconds:
//   - a press is reported on the scan that first sees it (eager);
//   - after a press the key ignores further changes for D ms;
//   - a release is reported once the key has stayed released for D ms (defer).
// D = 0 passes the matrix through unchanged.

#include "debounce.h"
#include "debounce_runtime.h"
#include "timer.h"
#include "util.h"
#include <string.h>

#define DEBOUNCE_ELAPSED 0

typedef struct {
    bool    pressed : 1;
    uint8_t time : 7;
} debounce_counter_t;

_Static_assert(ATELIER_DEBOUNCE_MAX <= 127, "debounce counter is 7 bits wide");

static uint8_t debounce_ms = ATELIER_DEBOUNCE_DEFAULT;

static debounce_counter_t debounce_counters[MATRIX_ROWS_PER_HAND * MATRIX_COLS];
static bool               counters_need_update;
static bool               matrix_need_update;
static bool               cooked_changed;

static void reset_counters(void) {
    memset(debounce_counters, 0, sizeof(debounce_counters));
    counters_need_update = false;
    // Re-evaluate every key on the next scan, in case one was mid-debounce.
    matrix_need_update = true;
}

void atelier_debounce_set(uint8_t ms) {
    if (ms > ATELIER_DEBOUNCE_MAX) {
        ms = ATELIER_DEBOUNCE_MAX;
    }
    if (ms != debounce_ms) {
        debounce_ms = ms;
        reset_counters();
    }
}

uint8_t atelier_debounce_get(void) {
    return debounce_ms;
}

void debounce_init(void) {
    reset_counters();
    matrix_need_update = false;
}

static inline void update_counters_and_transfer_if_expired(matrix_row_t raw[], matrix_row_t cooked[], uint8_t elapsed_time) {
    counters_need_update = false;
    matrix_need_update   = false;

    for (uint8_t row = 0; row < MATRIX_ROWS_PER_HAND; row++) {
        uint16_t row_offset = row * MATRIX_COLS;

        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            debounce_counter_t *counter = &debounce_counters[row_offset + col];

            if (counter->time == DEBOUNCE_ELAPSED) {
                continue;
            }
            if (counter->time <= elapsed_time) {
                counter->time = DEBOUNCE_ELAPSED;

                if (counter->pressed) {
                    // Lock-out after a press is over: look at the key again.
                    matrix_need_update = true;
                } else {
                    // The key stayed released long enough: report it.
                    matrix_row_t col_mask    = (MATRIX_ROW_SHIFTER << col);
                    matrix_row_t cooked_next = (cooked[row] & ~col_mask) | (raw[row] & col_mask);
                    cooked_changed |= cooked_next ^ cooked[row];
                    cooked[row] = cooked_next;
                }
            } else {
                counter->time -= elapsed_time;
                counters_need_update = true;
            }
        }
    }
}

static inline void transfer_matrix_values(matrix_row_t raw[], matrix_row_t cooked[]) {
    matrix_need_update = false;

    for (uint8_t row = 0; row < MATRIX_ROWS_PER_HAND; row++) {
        uint16_t     row_offset = row * MATRIX_COLS;
        matrix_row_t delta      = raw[row] ^ cooked[row];

        for (uint8_t col = 0; col < MATRIX_COLS; col++) {
            debounce_counter_t *counter  = &debounce_counters[row_offset + col];
            matrix_row_t        col_mask = (MATRIX_ROW_SHIFTER << col);

            if (delta & col_mask) {
                if (counter->time == DEBOUNCE_ELAPSED) {
                    counter->pressed     = (raw[row] & col_mask);
                    counter->time        = debounce_ms;
                    counters_need_update = true;

                    if (counter->pressed) {
                        // Press: report now.
                        cooked[row] ^= col_mask;
                        cooked_changed = true;
                    }
                }
            } else if (counter->time != DEBOUNCE_ELAPSED) {
                if (!counter->pressed) {
                    // Bounced back to pressed while waiting to release: cancel.
                    counter->time = DEBOUNCE_ELAPSED;
                }
            }
        }
    }
}

bool debounce(matrix_row_t raw[], matrix_row_t cooked[], bool changed) {
    static fast_timer_t last_time;
    bool                updated_last = false;
    cooked_changed                   = false;

    if (debounce_ms == 0) {
        for (uint8_t row = 0; row < MATRIX_ROWS_PER_HAND; row++) {
            cooked_changed |= (raw[row] != cooked[row]);
            cooked[row] = raw[row];
        }
        matrix_need_update = false;
        return cooked_changed;
    }

    if (counters_need_update) {
        fast_timer_t now          = timer_read_fast();
        fast_timer_t elapsed_time = TIMER_DIFF_FAST(now, last_time);

        last_time    = now;
        updated_last = true;

        if (elapsed_time > 0) {
            update_counters_and_transfer_if_expired(raw, cooked, MIN(elapsed_time, 127));
        }
    }

    if (changed || matrix_need_update) {
        if (!updated_last) {
            last_time = timer_read_fast();
        }
        transfer_matrix_values(raw, cooked);
    }

    return cooked_changed;
}

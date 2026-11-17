/*
 * Atelier rev 2.0: debounce for the Esc and Retry tact switches (issue #12).
 * GPL-3.0-or-later, like the libhmk it extends.
 *
 * Eager debounce: a change of the raw level is reported on the first sample,
 * then the key is locked for DIGITAL_DEBOUNCE_MS so contact bounce cannot
 * produce extra presses. Pure C, no hardware: tested on the host.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#if !defined(DIGITAL_DEBOUNCE_MS)
#define DIGITAL_DEBOUNCE_MS 5
#endif

typedef struct {
  bool state;     // debounced level, true = pressed
  bool locked;    // inside the lockout after a change
  uint32_t since; // time of the last change (ms)
} debounce_t;

static inline bool debounce_update(debounce_t *d, bool raw, uint32_t now) {
  if (d->locked && (uint32_t)(now - d->since) < DIGITAL_DEBOUNCE_MS)
    return d->state;
  d->locked = false;
  if (raw != d->state) {
    d->state = raw;
    d->locked = true;
    d->since = now;
  }
  return d->state;
}

// A button as the ADC reading of an analog key: at rest, or fully pressed.
static inline uint16_t digital_key_value(bool pressed, uint16_t rest,
                                         uint16_t full_scale) {
  return pressed ? full_scale : rest;
}

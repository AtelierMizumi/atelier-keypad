/*
 * Atelier rev 2.0: buttons read as libhmk keys (issue #12). GPL-3.0-or-later.
 *
 * Keys DIGITAL_KEYS_FIRST .. NUM_KEYS-1 are GPIO buttons to GND (internal
 * pull-up). matrix.c asks digital_keys_adc() for their "ADC value", so every
 * libhmk feature (keymap, layers, configurator) works for them unchanged.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "digital_debounce.h"
#include "digital_keys_config.h"

void digital_keys_init(void);

static inline bool digital_keys_is_digital(uint32_t key) {
  return key >= DIGITAL_KEYS_FIRST;
}

uint16_t digital_keys_adc(uint32_t key);

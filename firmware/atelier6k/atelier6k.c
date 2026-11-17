// Copyright 2026 thuanc177
// SPDX-License-Identifier: GPL-2.0-or-later
#include "atelier6k.h"
#include "debounce_runtime.h"

typedef struct {
    uint8_t debounce_ms;
} atelier_config_t;

_Static_assert(sizeof(atelier_config_t) == EECONFIG_KB_DATA_SIZE, "EECONFIG_KB_DATA_SIZE must match atelier_config_t");

static atelier_config_t config = {.debounce_ms = ATELIER_DEBOUNCE_DEFAULT};

static void config_save(void) {
    eeconfig_update_kb_datablock(&config, 0, sizeof(config));
}

void eeconfig_init_kb(void) {
    config.debounce_ms = ATELIER_DEBOUNCE_DEFAULT;
    config_save();
    eeconfig_init_user();
}

void keyboard_post_init_kb(void) {
    eeconfig_read_kb_datablock(&config, 0, sizeof(config));
    if (config.debounce_ms > ATELIER_DEBOUNCE_MAX) {
        // Blank or corrupted storage: fall back to the default.
        config.debounce_ms = ATELIER_DEBOUNCE_DEFAULT;
    }
    atelier_debounce_set(config.debounce_ms);
    keyboard_post_init_user();
}

bool process_record_kb(uint16_t keycode, keyrecord_t *record) {
    if (!process_record_user(keycode, record)) {
        return false;
    }
    if (keycode == AT_MODE) {
        if (record->event.pressed) {
            uint8_t next = (get_highest_layer(default_layer_state) + 1) % MODE_COUNT;
            set_single_persistent_default_layer(next);
        }
        return false;
    }
    return true;
}

#ifdef RGB_MATRIX_ENABLE
// The underglow shows which mode layer is active.
bool rgb_matrix_indicators_advanced_kb(uint8_t led_min, uint8_t led_max) {
    if (!rgb_matrix_indicators_advanced_user(led_min, led_max)) {
        return false;
    }
    static const uint8_t mode_hue[MODE_COUNT] = {
        [MODE_OSU]   = 234, // pink
        [MODE_TAIKO] = 14,  // orange
        [MODE_MANIA] = 170, // blue
    };
    uint8_t mode = get_highest_layer(default_layer_state);
    if (mode >= MODE_COUNT) {
        mode = MODE_OSU;
    }
    rgb_t rgb = hsv_to_rgb((hsv_t){mode_hue[mode], 255, rgb_matrix_get_val()});
    for (uint8_t i = led_min; i < led_max; i++) {
        if (g_led_config.flags[i] & LED_FLAG_UNDERGLOW) {
            rgb_matrix_set_color(i, rgb.r, rgb.g, rgb.b);
        }
    }
    return true;
}
#endif

#ifdef VIA_ENABLE
// VIA custom menu ("Keys" in via.json), channel id_custom_channel.
enum via_atelier_value {
    id_debounce_ms = 1,
};

void via_custom_value_command_kb(uint8_t *data, uint8_t length) {
    uint8_t *command_id = &data[0];
    uint8_t *channel_id = &data[1];
    uint8_t *value_id   = &data[2];
    uint8_t *value      = &data[3];

    if (*channel_id == id_custom_channel && *value_id == id_debounce_ms) {
        switch (*command_id) {
            case id_custom_set_value:
                atelier_debounce_set(*value);
                config.debounce_ms = atelier_debounce_get();
                return;
            case id_custom_get_value:
                *value = atelier_debounce_get();
                return;
            case id_custom_save:
                config_save();
                return;
        }
    }
    *command_id = id_unhandled;
}
#endif

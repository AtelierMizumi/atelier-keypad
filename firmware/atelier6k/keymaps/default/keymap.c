// Copyright 2026 thuanc177
// SPDX-License-Identifier: GPL-2.0-or-later
#include QMK_KEYBOARD_H

/*
 *        K1   K2   K3
 *  B1      K4   K5   K6
 *  B2
 *  B3
 *
 * B1 = Esc, B2 = quick retry, B3 = next mode. The underglow colour shows the
 * mode: pink osu!, orange taiko, blue mania. No tap-hold keys anywhere, so
 * every press is sent on the scan that sees it.
 */
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [MODE_OSU] = LAYOUT(
        KC_A,    KC_S,    KC_D,
        KC_Z,    KC_X,    KC_C,
        KC_ESC,  KC_GRV,  AT_MODE
    ),
    // kat, don / don, kat
    [MODE_TAIKO] = LAYOUT(
        KC_Z,    KC_X,    KC_NO,
        KC_C,    KC_V,    KC_NO,
        KC_ESC,  KC_GRV,  AT_MODE
    ),
    // 6K; for 4K use D F / J K in osu!'s key settings
    [MODE_MANIA] = LAYOUT(
        KC_S,    KC_D,    KC_F,
        KC_J,    KC_K,    KC_L,
        KC_ESC,  KC_GRV,  AT_MODE
    ),
    [3] = LAYOUT(
        KC_TRNS, KC_TRNS, KC_TRNS,
        KC_TRNS, KC_TRNS, KC_TRNS,
        KC_TRNS, KC_TRNS, KC_TRNS
    ),
};

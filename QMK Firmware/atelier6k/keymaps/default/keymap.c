#include "atelier6k.h"
#include QMK_KEYBOARD_H

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {

[0] = LAYOUT(
	KC_A, KC_S, KC_D, 
	KC_Z, KC_X, KC_C, 
	LT(1, KC_ESC), LT(2, KC_ENT), LT(3, KC_NO)),

/* LAYER 0
 * .-----------------------.
 * |   A   |   S   |   D   |
 * |-------+-------+-------|
 * |   Z   |   X   |   C   |
 * '-----------------------'
 * .-----------------------.
 * |FN1/ESC|FN2/ENT|  FN3  |
 * '-----------------------'
 * 
 * FN1 is for function keys F1 -> F6
 * FN2 is for Lighting, first row is for Backlight, second row is for RGB
 * FN3 is also for lighting, this time changing modes and stuffs
 * 
 * I know I don't know what the heck am I gonna put in so, it's up to you mapping it via VIA (baddum tis) yourself :)
 */

[1] = LAYOUT(
	KC_F1, KC_F2, KC_F3, 
	KC_F4, KC_F5, KC_F6, 
	KC_TRNS, KC_TRNS, KC_TRNS),

[2] = LAYOUT(
	BL_TOGG, BL_INC, BL_DEC, 
	RGB_TOG, RGB_VAI, RGB_VAD, 
	KC_TRNS, KC_TRNS, KC_TRNS),

[3] = LAYOUT(
	RGB_MOD, RGB_HUI, RGB_HUD, 
	RESET, RGB_SAI, RGB_SAD, 
	KC_TRNS, KC_TRNS, KC_TRNS),

[4] = LAYOUT(
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS),

[5] = LAYOUT(
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS),

[6] = LAYOUT(
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS),

[7] = LAYOUT(
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS),

[8] = LAYOUT(
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS,
	KC_TRNS, KC_TRNS, KC_TRNS),
};


void matrix_init_user(void) {
}

void matrix_scan_user(void) {
}

bool process_record_user(uint16_t keycode, keyrecord_t *record) {
	return true;
}
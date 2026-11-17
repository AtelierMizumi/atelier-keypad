// Copyright 2026 thuanc177
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include "quantum.h"

// Layers 0..2 are the osu! modes; AT_MODE steps through them.
enum atelier_modes { MODE_OSU, MODE_TAIKO, MODE_MANIA, MODE_COUNT };

enum atelier_keycodes {
    AT_MODE = QK_KB_0, // switch to the next mode layer and remember it
};

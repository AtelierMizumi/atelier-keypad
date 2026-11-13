// Copyright 2026 thuanc177
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Behaviour of the runtime-adjustable debounce, with D = the configured time:
//   - a press is reported on the scan that first sees it;
//   - after a press the key ignores changes for D ms;
//   - a release is reported once the key has stayed released for D ms;
//   - D can be changed at runtime, 0 disables debouncing, and values above
//     the maximum are clamped.

#include "gtest/gtest.h"

#include "debounce_test_common.h"

extern "C" {
#include "debounce_runtime.h"
}

TEST_F(DebounceTest, DefaultIsFiveMilliseconds) {
    atelier_debounce_set(ATELIER_DEBOUNCE_DEFAULT);
    EXPECT_EQ(atelier_debounce_get(), 5);
    addEvents({
        {0, {{0, 1, DOWN}}, {{0, 1, DOWN}}}, /* press: reported at once */
        {1, {{0, 1, UP}}, {}},

        {5, {}, {}},

        {10, {}, {{0, 1, UP}}}, /* 5 ms lock-out + 5 ms stable release */
        {11, {{0, 1, DOWN}}, {{0, 1, DOWN}}},
    });
    runEvents();
}

TEST_F(DebounceTest, OneMillisecond) {
    atelier_debounce_set(1);
    addEvents({
        {0, {{0, 1, DOWN}}, {{0, 1, DOWN}}},
        {1, {{0, 1, UP}}, {}},
        {2, {}, {{0, 1, UP}}}, /* 1 ms lock-out + 1 ms stable release */
        {3, {{0, 1, DOWN}}, {{0, 1, DOWN}}},
    });
    runEvents();
}

TEST_F(DebounceTest, TenMillisecondsHoldsTheReleaseLonger) {
    atelier_debounce_set(10);
    addEvents({
        {0, {{0, 1, DOWN}}, {{0, 1, DOWN}}},
        {3, {{0, 1, UP}}, {}},
        {10, {}, {}}, /* a scan when the lock-out ends; the harness only scans at listed times */
        {19, {}, {}},
        {20, {}, {{0, 1, UP}}}, /* 10 ms lock-out + 10 ms stable release */
    });
    runEvents();
}

TEST_F(DebounceTest, ZeroDisablesDebouncing) {
    atelier_debounce_set(0);
    addEvents({
        {0, {{0, 1, DOWN}}, {{0, 1, DOWN}}},
        {1, {{0, 1, UP}}, {{0, 1, UP}}},
        {2, {{0, 1, DOWN}}, {{0, 1, DOWN}}},
        {3, {{0, 1, UP}}, {{0, 1, UP}}},
    });
    runEvents();
}

TEST_F(DebounceTest, BounceDuringReleaseDoesNotRetrigger) {
    atelier_debounce_set(5);
    addEvents({
        {0, {{0, 1, DOWN}}, {{0, 1, DOWN}}},
        {20, {{0, 1, UP}}, {}},
        {22, {{0, 1, DOWN}}, {}}, /* contact bounce: the key never left "pressed" */
        {23, {{0, 1, UP}}, {}},
        {27, {}, {}},
        {28, {}, {{0, 1, UP}}}, /* 5 ms after the last bounce */
    });
    runEvents();
}

TEST_F(DebounceTest, BounceDuringPressIsIgnored) {
    atelier_debounce_set(5);
    addEvents({
        {0, {{0, 1, DOWN}}, {{0, 1, DOWN}}},
        {1, {{0, 1, UP}}, {}},
        {2, {{0, 1, DOWN}}, {}},
        {40, {}, {}}, /* still pressed, exactly one DOWN was reported */
    });
    runEvents();
}

TEST_F(DebounceTest, KeysAreIndependent) {
    atelier_debounce_set(5);
    addEvents({
        {0, {{0, 1, DOWN}}, {{0, 1, DOWN}}},
        {2, {{0, 2, DOWN}}, {{0, 2, DOWN}}}, /* second key is not delayed by the first */
        {20, {{0, 1, UP}}, {}},
        {25, {}, {{0, 1, UP}}},
        {30, {{0, 2, UP}}, {}},
        {35, {}, {{0, 2, UP}}},
    });
    runEvents();
}

TEST(DebounceRuntimeSetting, ClampsToMaximum) {
    atelier_debounce_set(200);
    EXPECT_EQ(atelier_debounce_get(), ATELIER_DEBOUNCE_MAX);
    atelier_debounce_set(ATELIER_DEBOUNCE_MAX);
    EXPECT_EQ(atelier_debounce_get(), ATELIER_DEBOUNCE_MAX);
    atelier_debounce_set(7);
    EXPECT_EQ(atelier_debounce_get(), 7);
    atelier_debounce_set(ATELIER_DEBOUNCE_DEFAULT);
}

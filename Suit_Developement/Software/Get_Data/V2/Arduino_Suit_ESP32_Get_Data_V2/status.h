#pragma once

#include "types.h"

// ======================================================
// STATUS
// ======================================================

void initializeStatus();

void setSystemState(SystemState state);

SystemState getSystemState();

/**
 * @brief Update LEDs immediately.
 */
void refreshStatus();

/**
 * @brief Update LEDs continuously.
 */
void updateStatus();
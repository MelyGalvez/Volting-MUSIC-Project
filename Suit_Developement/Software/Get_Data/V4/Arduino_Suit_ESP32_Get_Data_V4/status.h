#pragma once

#include "types.h"


// ================================================
// STATUS.h
// ================================================


void initializeStatus();


void setSystemState(SystemState state);


SystemState getSystemState();


/**
 * @brief Wire-protocol name of a system state.
 */
const char* systemStateName(SystemState state);


/**
 * @brief Update LEDs immediately.
 */
void refreshStatus();


/**
 * @brief Drive the calibration blink pattern (call from loop).
 */
void updateStatus();

#pragma once

#include "types.h"


// ================================================
// SNAPSHOT.h
// ================================================


/**
 * @brief Create the mutex. Call once before any task starts.
 */
void initializeSnapshot();


/**
 * @brief Publish a complete IMU scan (bumps seq + timestamp).
 */
void snapshotPublishImu(const ImuFrame frames[NUM_IMUS]);


/**
 * @brief Update the piezo section of the snapshot.
 */
void snapshotUpdatePiezo(
    const PiezoChannelState& left,
    const PiezoChannelState& right
);


/**
 * @brief Copy the latest self-consistent snapshot.
 */
void snapshotGet(Snapshot& out);

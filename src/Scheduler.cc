//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Lesser General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Lesser General Public License for more details.
// 
// You should have received a copy of the GNU Lesser General Public License
// along with this program.  If not, see http://www.gnu.org/licenses/.
// 

#include "Scheduler.h"

Define_Module(Scheduler);

const int Scheduler::cqiToBytesPerRB[16] = {
    0,   // CQI 0 (not used)
    3,   // CQI 1
    3,   // CQI 2
    6,   // CQI 3
    11,  // CQI 4
    15,  // CQI 5
    20,  // CQI 6
    25,  // CQI 7
    36,  // CQI 8
    39,  // CQI 9
    50,  // CQI 10
    63,  // CQI 11
    72,  // CQI 12
    80,  // CQI 13
    93,  // CQI 14
    93   // CQI 15
};

void Scheduler::initialize()
{
    // Get parameters
    numUsers = par("numUsers");
    numResourceBlocks = par("numResourceBlocks");
    ttiDuration = par("ttiDuration");

    // Initialize round-robin state
    currentUserIndex = 0;
    ttiCounter = 0;

    // Initialize user data structures
    userCQI.resize(numUsers, 1);  // Default CQI
    userQueues.resize(numUsers);
    cqiReceived.resize(numUsers, false);
    cqiReceivedCount = 0;

    // Get pointers to queue modules
    cModule *parent = getParentModule();
    for (int i = 0; i < numUsers; i++) {
        cModule *queueModule = parent->getSubmodule("queue", i);
        userQueues[i] = check_and_cast<FIFOQueue*>(queueModule);
    }

    // Initialize statistics
    scheduledUsersSignal = registerSignal("scheduledUsers");
    rbUtilizationSignal = registerSignal("rbUtilization");
    transmittedBytesSignal = registerSignal("transmittedBytes");

    lastMetricCalculation = simTime();

    // Schedule first TTI
    ttiEvent = new cMessage("TTI");
    scheduleAt(simTime() + ttiDuration, ttiEvent);

    EV << "Scheduler initialized with " << numUsers << " users\n";
}

void Scheduler::handleMessage(cMessage *msg)
{
    if (msg == ttiEvent) {
        handleTTIEvent();
    }
    else if (CQIReport *report = check_and_cast<CQIReport*>(msg)) {
        handleCQIReport(report);
    }
    else {
        EV_ERROR << "Unknown message type received\n";
        delete msg;
    }
}

void Scheduler::handleCQIReport(CQIReport *report)
{
    int userId = report->getUserId();
    int cqi = report->getCqiValue();

    if (userId >= 0 && userId < numUsers && cqi >= 1 && cqi <= 15) {
        userCQI[userId] = cqi;

        // Mark CQI as received
        if (!cqiReceived[userId]) {
            cqiReceived[userId] = true;
            cqiReceivedCount++;
        }

        EV_DEBUG << "Updated CQI for user " << userId << " to " << cqi
                 << " (received " << cqiReceivedCount << "/" << numUsers << ")\n";
    }

    delete report;

    if (cqiReceivedCount == numUsers){
        startScheduling();
    }
}

void Scheduler::handleTTIEvent()
{
    ttiCounter++;
    EV_DEBUG << "=== TTI " << ttiCounter << " at " << simTime() << "s ===\n";

    // Request CQI updates from all users
    requestCQIUpdates();

    // Schedule next TTI
    scheduleAt(simTime() + ttiDuration, ttiEvent);
}

void Scheduler::startScheduling()
{
    // Perform scheduling
    performRoundRobinScheduling();

    // Reset CQI collection for next TTI
    resetCQICollection();
}

void Scheduler::requestCQIUpdates()
{
    // Send CQI request to all users
    for (int i = 0; i < numUsers; i++) {
        cMessage *cqiRequest = new cMessage("CQIRequest");
        cqiRequest->setKind(1000);  // Special kind for CQI requests
        send(cqiRequest, "toUsers", i);
    }
}

void Scheduler::resetCQICollection()
{
    for (int i = 0; i < numUsers; i++) {
        cqiReceived[i] = false;
    }
    cqiReceivedCount = 0;
}

void Scheduler::performRoundRobinScheduling()
{
    int startIndex = currentUserIndex;
    int rbsUsedThisTTI = 0;
    int rbsRemaining = numResourceBlocks;
    int numUsersThisTTI = 0;
    int bytesTransmittedThisTTI = 0;

    EV_DEBUG << "RoundRobinScheduling for TTI: " << ttiCounter << endl;

    // Find next user with packets
    do {
        if (!userQueues[currentUserIndex]->isEmpty()) {

            // Get user's channel quality
            int cqi = userCQI[currentUserIndex];
            int bytesPerRB = getBytesPerRB(cqi);

            EV_DEBUG << "TTI " << ttiCounter << ": Scheduling user " << currentUserIndex
                     << " with CQI=" << cqi << " (bytes/RB=" << bytesPerRB << ")\n";

            // Get packets that can be transmitted
            QueueResult* packetsToTransmit =
                userQueues[currentUserIndex]->getPacketsToTransmit(bytesPerRB, rbsRemaining);

            // Process transmitted packets
            if (packetsToTransmit->getBytesToTransmit()>0) {
                numUsersThisTTI++;
                bytesTransmittedThisTTI +=packetsToTransmit->getBytesToTransmit();

                rbsRemaining -= packetsToTransmit->getRbUsed();
                rbsUsedThisTTI += packetsToTransmit->getRbUsed();


                EV_DEBUG << "TTI " << ttiCounter << ": Scheduling user " << currentUserIndex
                        << "  Total transmitted: " << packetsToTransmit->getBytesToTransmit()
                        << " bytes using " << packetsToTransmit->getRbUsed() << " RBs\n";

                // Send scheduling grant
                sendSchedulingGrant(currentUserIndex,
                        packetsToTransmit->getBytesToTransmit(),
                        packetsToTransmit->getRbUsed());
            }
        }
        currentUserIndex = (currentUserIndex + 1) % numUsers;
    } while (currentUserIndex != startIndex && rbsRemaining > 0);

    EV_DEBUG << "Total RBs used: " << rbsUsedThisTTI << endl;

    // Advance to next user for next TTI
    currentUserIndex = (startIndex + 1) % numUsers;

    emit(rbUtilizationSignal, rbsUsedThisTTI);
    emit(scheduledUsersSignal, numUsersThisTTI);
    emit(transmittedBytesSignal, bytesTransmittedThisTTI);
}

int Scheduler::getBytesPerRB(int cqi)
{
    if (cqi >= 1 && cqi <= 15) {
        return cqiToBytesPerRB[cqi];
    }
    return 0;
}

void Scheduler::sendSchedulingGrant(int userId, int allocatedBytes, int allocatedRBs)
{
    SchedulingGrant *grant = new SchedulingGrant("SchedulingGrant");
    grant->setUserId(userId);
    grant->setAllocatedBytes(allocatedBytes);
    grant->setAllocatedRBs(allocatedRBs);

    send(grant, "toUsers", userId);
}

void Scheduler::finish()
{
    cancelAndDelete(ttiEvent);

    EV << "Scheduler finished. Total TTIs: " << ttiCounter << "\n";
}

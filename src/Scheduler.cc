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

// CQI to bytes per RB mapping based on project specification
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
    schedulingAlgorithm = par("schedulingAlgorithm").stringValue();

    // Get warmup period from simulation configuration
    warmupPeriod = getSimulation()->getWarmupPeriod();

    // Initialize round-robin state
    currentUserIndex = 0;
    ttiCounter = 0;

    // Initialize user data structures
    userCQI.resize(numUsers, 8);  // Default CQI
    userQueues.resize(numUsers);
    userBytesTransmitted.resize(numUsers, 0);
    userPacketsTransmitted.resize(numUsers, 0);
    cqiReceived.resize(numUsers, false);
    cqiReceivedCount = 0;

    // Get pointers to queue modules
    cModule *parent = getParentModule();
    for (int i = 0; i < numUsers; i++) {
        cModule *queueModule = parent->getSubmodule("queue", i);
        userQueues[i] = check_and_cast<FIFOQueue*>(queueModule);

        // Initialize per-user statistics vectors
        char vectorName[50];
        sprintf(vectorName, "userResponseTime%d", i);
        cOutVector *respVector = new cOutVector(vectorName);
        userResponseTimeVectors.push_back(respVector);

        sprintf(vectorName, "userThroughput%d", i);
        cOutVector *thrVector = new cOutVector(vectorName);
        userThroughputVectors.push_back(thrVector);
    }

    // Initialize statistics
    throughputVector.setName("systemThroughput");
    fairnessVector.setName("fairnessIndex");
    rbUtilizationVector.setName("rbUtilization");
    packetsInSystemVector.setName("packetsInSystem");

    lastMetricCalculation = simTime();
    totalBytesTransmitted = 0;
    totalRBsUsed = 0;
    totalPacketsInSystem = 0;  // Initialize the missing variable

    // Steady state detection
    steadyStateCheckInterval = 10.0;
    lastSteadyStateCheck = 0;
    historySize = 30;
    steadyStateReached = false;
    varianceThreshold = 0.01;

    // Schedule first TTI
    ttiEvent = new cMessage("TTI");
    scheduleAt(simTime() + ttiDuration, ttiEvent);

    EV << "Scheduler initialized with " << numUsers << " users\n";
    EV << "Warmup period: " << warmupPeriod << "s\n";
}

void Scheduler::handleMessage(cMessage *msg)
{
    if (msg == ttiEvent) {
        handleTTIEvent();
    }
    else if (CQIReport *report = dynamic_cast<CQIReport*>(msg)) {
        handleCQIReport(report);
    }
    else {
        EV_WARN << "Unknown message type received\n";
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
}

void Scheduler::handleTTIEvent()
{
    ttiCounter++;

    // Request CQI updates from all users
    requestCQIUpdates();

    // Wait for all CQI reports before scheduling
    if (cqiReceivedCount == numUsers) {
        // Perform scheduling
        performRoundRobinScheduling();

        // Reset CQI collection for next TTI
        resetCQICollection();

        // Update queue statistics
        updateQueueStatistics();

        // Calculate metrics periodically (only after warmup)
        if (!isWarmupPeriod() && ttiCounter % 100 == 0) {
            calculateMetrics();
        }

        // Check for steady state (only after warmup)
        if (!isWarmupPeriod() && simTime() - lastSteadyStateCheck >= steadyStateCheckInterval) {
            checkSteadyState();
        }
    }

    // Schedule next TTI
    scheduleAt(simTime() + ttiDuration, ttiEvent);
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

    // Find next user with packets
    do {
        if (!userQueues[currentUserIndex]->isEmpty()) {

            // Get user's channel quality
            int cqi = userCQI[currentUserIndex];
            int bytesPerRB = getBytesPerRB(cqi);

            EV_DEBUG << "TTI " << ttiCounter << ": Scheduling user " << currentUserIndex
                     << " with CQI=" << cqi << " (bytes/RB=" << bytesPerRB << ")\n";

            // Get packets that can be transmitted
            std::vector<DataPacket*> packetsToTransmit =
                userQueues[currentUserIndex]->getPacketsToTransmit(bytesPerRB, rbsRemaining);

            // Process transmitted packets
            if (!packetsToTransmit.empty()) {
                int totalBytesTransmitted = 0;

                for (DataPacket *packet : packetsToTransmit) {
                    // Calculate response time
                    simtime_t responseTime = simTime() - packet->getCreationTime();

                    // Record statistics only after warmup
                    if (!isWarmupPeriod()) {
                        userResponseTimeVectors[currentUserIndex]->record(responseTime);

                        // Emit response time signal
                        char signalName[50];
                        sprintf(signalName, "userResponseTime%d", currentUserIndex);
                        simsignal_t signal = registerSignal(signalName);
                        emit(signal, responseTime);
                    }

                    // Update statistics
                    int packetBytes = packet->getByteLength();
                    totalBytesTransmitted += packetBytes;

                    if (!isWarmupPeriod()) {
                        userBytesTransmitted[currentUserIndex] += packetBytes;
                        userPacketsTransmitted[currentUserIndex]++;
                        this->totalBytesTransmitted += packetBytes;
                    }

                    EV_DEBUG << "  Transmitted packet: " << packetBytes << " bytes, "
                             << "response time: " << responseTime << "s\n";

                    delete packet;
                }

                // Calculate RBs used
                rbsUsedThisTTI = (totalBytesTransmitted + bytesPerRB - 1) / bytesPerRB;
                rbsRemaining -= rbsUsedThisTTI;

                if (!isWarmupPeriod()) {
                    totalRBsUsed += rbsUsedThisTTI;
                }

                // Send scheduling grant
                sendSchedulingGrant(currentUserIndex, totalBytesTransmitted, rbsUsedThisTTI);

                EV_DEBUG << "  Total transmitted: " << totalBytesTransmitted << " bytes using "
                         << rbsUsedThisTTI << " RBs\n";
            }

            break;
        }

        currentUserIndex = (currentUserIndex + 1) % numUsers;
    } while (currentUserIndex != startIndex);

    // Advance to next user for next TTI
    currentUserIndex = (currentUserIndex + 1) % numUsers;

    // Record RB utilization (only after warmup)
    if (!isWarmupPeriod()) {
        double utilization = (double)rbsUsedThisTTI / numResourceBlocks;
        rbUtilizationVector.record(utilization);
        rbUtilizationHistory.push_back(utilization);  // Store for mean calculation
        emit(registerSignal("rbUtilization"), utilization);
    }
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

void Scheduler::calculateMetrics()
{
    simtime_t currentTime = simTime();
    simtime_t interval = currentTime - lastMetricCalculation;

    if (interval > 0) {
        // Calculate system throughput (Mbps)
        double systemThroughput = (totalBytesTransmitted * 8.0) / (interval.dbl() * 1e6);
        throughputVector.record(systemThroughput);
        emit(registerSignal("throughput"), systemThroughput);

        // Store throughput for steady state detection
        throughputHistory.push_back(systemThroughput);
        if (throughputHistory.size() > (size_t)historySize) {
            throughputHistory.pop_front();
        }

        // Calculate per-user throughputs
        std::vector<double> userThroughputs(numUsers);
        for (int i = 0; i < numUsers; i++) {
            userThroughputs[i] = (userBytesTransmitted[i] * 8.0) / (interval.dbl() * 1e6);
            userThroughputVectors[i]->record(userThroughputs[i]);

            char signalName[50];
            sprintf(signalName, "userThroughput%d", i);
            emit(registerSignal(signalName), userThroughputs[i]);
        }

        // Calculate Jain's fairness index
        double fairness = calculateJainsFairnessIndex(userThroughputs);
        fairnessVector.record(fairness);
        emit(registerSignal("fairnessIndex"), fairness);

        EV << "Metrics at " << currentTime << "s:\n"
           << "  System throughput: " << systemThroughput << " Mbps\n"
           << "  Fairness index: " << fairness << "\n"
           << "  Total queue length: " << getTotalQueueLength() << "\n";

        // Reset counters
        totalBytesTransmitted = 0;
        for (int i = 0; i < numUsers; i++) {
            userBytesTransmitted[i] = 0;
        }
        lastMetricCalculation = currentTime;
    }
}

double Scheduler::calculateJainsFairnessIndex(const std::vector<double>& throughputs)
{
    double sum = 0;
    double sumSquares = 0;
    int n = throughputs.size();

    for (double t : throughputs) {
        sum += t;
        sumSquares += t * t;
    }

    if (sumSquares > 0) {
        return (sum * sum) / (n * sumSquares);
    }
    return 1.0;  // Perfect fairness if all zero
}

int Scheduler::getTotalQueueLength()
{
    int total = 0;
    for (int i = 0; i < numUsers; i++) {
        total += userQueues[i]->getLength();
    }
    return total;
}

void Scheduler::updateQueueStatistics()
{
    // Count total packets in system
    totalPacketsInSystem = getTotalQueueLength();

    // Record statistics only after warmup
    if (!isWarmupPeriod()) {
        packetsInSystemVector.record(totalPacketsInSystem);
        emit(registerSignal("packetsInSystem"), (long)totalPacketsInSystem);
    }
}

void Scheduler::checkSteadyState()
{
    // Check if we have enough history
    if (throughputHistory.size() < (size_t)historySize) {
        lastSteadyStateCheck = simTime();
        return;
    }

    // Calculate mean and variance of throughput history
    double mean = 0;
    for (double t : throughputHistory) {
        mean += t;
    }
    mean /= throughputHistory.size();

    double variance = calculateVariance(throughputHistory);
    double coefficientOfVariation = (mean > 0) ? sqrt(variance) / mean : 0;

    EV << "Steady state check at " << simTime() << "s:\n"
       << "  Mean throughput: " << mean << " Mbps\n"
       << "  Variance: " << variance << "\n"
       << "  Coefficient of variation: " << coefficientOfVariation << "\n";

    // Check if variance is below threshold
    if (coefficientOfVariation < varianceThreshold) {
        if (!steadyStateReached) {
            steadyStateReached = true;
            EV << "STEADY STATE reached at time " << simTime() << "s\n";
            recordScalar("steadyStateTime", simTime().dbl());
            recordScalar("steadyStateMeanThroughput", mean);
            recordScalar("steadyStateVariance", variance);
        }
    } else {
        steadyStateReached = false;  // System left steady state
    }

    lastSteadyStateCheck = simTime();
}

double Scheduler::calculateVariance(const std::deque<double>& values)
{
    if (values.size() < 2) {
        return 0;
    }

    double mean = 0;
    for (double v : values) {
        mean += v;
    }
    mean /= values.size();

    double variance = 0;
    for (double v : values) {
        double diff = v - mean;
        variance += diff * diff;
    }
    variance /= (values.size() - 1);  // Sample variance

    return variance;
}

double Scheduler::calculateMean(const std::vector<double>& values)
{
    if (values.empty()) {
        return 0.0;
    }

    double sum = 0.0;
    for (double v : values) {
        sum += v;
    }
    return sum / values.size();
}

void Scheduler::finish()
{
    // Record final statistics
    recordScalar("totalTTIs", ttiCounter);
    // Use our custom mean calculation instead of non-existent getMean()
    double avgRBUtilization = calculateMean(rbUtilizationHistory);
    recordScalar("avgRBUtilization", avgRBUtilization);

    // Clean up
    for (int i = 0; i < numUsers; i++) {
        delete userResponseTimeVectors[i];
        delete userThroughputVectors[i];
    }

    cancelAndDelete(ttiEvent);

    // Print final statistics
    EV << "Scheduler finished. Total TTIs: " << ttiCounter << "\n";
}

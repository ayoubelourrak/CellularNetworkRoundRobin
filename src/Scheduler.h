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

#ifndef __CELLULARROUNDROBIN_SCHEDULER_H_
#define __CELLULARROUNDROBIN_SCHEDULER_H_

#include <omnetpp.h>
#include <vector>
#include <deque>
#include "Messages_m.h"
#include "FIFOQueue.h"

using namespace omnetpp;

/**
 * Round-Robin Scheduler implementation
 */
class Scheduler : public cSimpleModule
{
    private:
        // Configuration parameters
        int numUsers;
        int numResourceBlocks;
        simtime_t ttiDuration;
        std::string schedulingAlgorithm;

        // Round-robin state
        int currentUserIndex;
        int ttiCounter;

        // User information
        std::vector<int> userCQI;
        std::vector<FIFOQueue*> userQueues;  // Pointers to queue modules
        std::vector<double> userBytesTransmitted;
        std::vector<int> userPacketsTransmitted;

        // CQI collection state
        std::vector<bool> cqiReceived;
        int cqiReceivedCount;

        // TTI self-message
        cMessage *ttiEvent;

        // Statistics
        cOutVector throughputVector;
        cOutVector fairnessVector;
        cOutVector rbUtilizationVector;
        cOutVector packetsInSystemVector;
        std::vector<cOutVector*> userResponseTimeVectors;
        std::vector<cOutVector*> userThroughputVectors;

        // Metrics tracking
        simtime_t lastMetricCalculation;
        double totalBytesTransmitted;
        int totalRBsUsed;
        int totalPacketsInSystem;  // Added missing declaration

        // CQI to bytes mapping (3GPP table from project spec)
        static const int cqiToBytesPerRB[16];

        // Steady state detection
        simtime_t steadyStateCheckInterval;
        simtime_t lastSteadyStateCheck;
        std::deque<double> throughputHistory;
        int historySize;
        bool steadyStateReached;
        double varianceThreshold;

        // Warmup period handling
        simtime_t warmupPeriod;
        bool isWarmupPeriod() const { return simTime() < warmupPeriod; }

        // RB utilization tracking for mean calculation
        std::vector<double> rbUtilizationHistory;

    protected:
        virtual void initialize() override;
        virtual void handleMessage(cMessage *msg) override;
        virtual void finish() override;

        // Scheduling functions
        void performRoundRobinScheduling();
        int getBytesPerRB(int cqi);

        // CQI management
        void requestCQIUpdates();
        void resetCQICollection();

        // Message handling
        void handleCQIReport(CQIReport *report);
        void handleTTIEvent();

        // Metrics calculation
        void calculateMetrics();
        double calculateJainsFairnessIndex(const std::vector<double>& throughputs);
        void checkSteadyState();
        double calculateVariance(const std::deque<double>& values);

        // Queue management
        int getTotalQueueLength();
        void updateQueueStatistics();

        // Utility functions
        void sendSchedulingGrant(int userId, int allocatedBytes, int allocatedRBs);
        double calculateMean(const std::vector<double>& values);  // Helper function for mean calculation
};

#endif

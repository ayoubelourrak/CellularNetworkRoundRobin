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

        // Round-robin state
        int currentUserIndex;
        long ttiCounter;

        // User information
        std::vector<int> userCQI;
        std::vector<FIFOQueue*> userQueues;

        // CQI collection state
        std::vector<bool> cqiReceived;
        int cqiReceivedCount;

        // TTI self-message
        cMessage *ttiEvent;

        // Statistics
        simsignal_t scheduledUsersSignal;
        simsignal_t rbUtilizationSignal;
        simsignal_t transmittedBytesSignal;


        // Metrics tracking
        simtime_t lastMetricCalculation;

        // CQI to bytes mapping
        static const int cqiToBytesPerRB[16];

    protected:
        virtual void initialize() override;
        virtual void handleMessage(cMessage *msg) override;
        virtual void finish() override;

        // Scheduling functions
        void performRoundRobinScheduling();
        void startScheduling();
        int getBytesPerRB(int cqi);

        // CQI management
        void requestCQIUpdates();
        void resetCQICollection();

        // Message handling
        void handleCQIReport(CQIReport *report);
        void handleTTIEvent();

        // Utility functions
        void sendSchedulingGrant(int userId, int allocatedBytes, int allocatedRBs);
};

#endif

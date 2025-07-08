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

#ifndef __CELLULARROUNDROBIN_USEREQUIPMENT_H_
#define __CELLULARROUNDROBIN_USEREQUIPMENT_H_

#include <omnetpp.h>
#include "Messages_m.h"

using namespace omnetpp;

class UserEquipment : public cSimpleModule
{
    private:
        // User identification
        int userId;

        // Traffic generation parameters
        double arrivalRate;
        int maxPacketSize;
        std::string arrivalPattern;
        std::string packetPattern;
        cMessage *nextArrivalEvent;
        unsigned long sequenceNumber;

        // Channel quality parameters
        int currentCQI;
        int maxCQI;
        std::string cqiModel;

        // Binomial CQI parameters
        int binomialN;
        double binomialP;

        // RNG streams
        int arrivalRngId;
        int sizeRngId;
        int cqiRngId;

        // Statistics
        simtime_t lastArrivalTime;
        simsignal_t packetsGeneratedSignal;
        simsignal_t cqiValueSignal;
        simsignal_t interArrivalTimeSignal;
        simsignal_t packetDimensionSignal;

    protected:
        virtual void initialize() override;
        virtual void handleMessage(cMessage *msg) override;
        virtual void finish() override;

        // Traffic generation
        void generatePacket();
        void scheduleNextArrival();
        double getNextArrivalInterval();
        int getPacketSize();

        // Channel quality management
        void updateCQI();
        void reportCQI();
        int generateCQI();

        // Message handling
        void handleArrivalEvent();
        void handleSchedulingGrant(SchedulingGrant *grant);
};

#endif

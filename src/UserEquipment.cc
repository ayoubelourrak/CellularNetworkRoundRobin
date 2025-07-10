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

#include "UserEquipment.h"

Define_Module(UserEquipment);

void UserEquipment::initialize()
{
    // Get parameters
        userId = par("userId");
        arrivalRate = par("arrivalRate");
        maxPacketSize = par("maxPacketSize");
        arrivalPattern = par("arrivalPattern").stringValue();
        packetPattern = par("packetPattern").stringValue();
        cqiModel = par("cqiModel").stringValue();
        maxCQI = par("maxCQI");

        // Get RNG stream IDs
        arrivalRngId = par("arrivalRngId");
        sizeRngId = par("sizeRngId");
        cqiRngId = par("cqiRngId");

        // Initialize binomial parameters if using binomial model
        if (cqiModel == "binomial") {
            binomialN = par("binomialN");
            binomialP = par("binomialP");
        }

        // Initialize statistics
        sequenceNumber = 0;
        lastArrivalTime = 0;
        packetsGeneratedSignal = registerSignal("packetGenerated");
        cqiValueSignal = registerSignal("cqiValue");
        interArrivalTimeSignal = registerSignal("interArrivalTime");
        packetDimensionSignal = registerSignal("packetDimension");

        // Generate initial CQI
        currentCQI = 0;

        // Schedule first packet arrival
        nextArrivalEvent = new cMessage("nextArrival");
        scheduleNextArrival();

        EV << "User " << userId << " initialized with arrival rate " << arrivalRate
           << " Hz, CQI model: " << cqiModel << "\n";
}

void UserEquipment::handleMessage(cMessage *msg)
{
    if (msg == nextArrivalEvent) {
        handleArrivalEvent();
    }
    else if (msg->getKind() == 1000) {  // CQI request from base station
        // Update and report CQI
        updateCQI();
        reportCQI();
        delete msg;
    }
    else if (SchedulingGrant *grant = check_and_cast<SchedulingGrant*>(msg)) {
        handleSchedulingGrant(grant);
    }
    else {
        EV_ERROR << "Unknown message type received\n";
        delete msg;
    }
}

void UserEquipment::handleArrivalEvent()
{
    // Generate new packet
    generatePacket();

    // Schedule next arrival
    scheduleNextArrival();
}

void UserEquipment::generatePacket()
{
    // Create packet
    DataPacket *packet = new DataPacket("dataPacket");
    packet->setUserId(userId);
    packet->setSequenceNumber(sequenceNumber++);
    packet->setByteLength(getPacketSize());
    packet->setCreationTime(simTime());

    emit(packetDimensionSignal, packet->getByteLength());

    // Record inter-arrival time
    if (lastArrivalTime > 0) {
        simtime_t interArrival = simTime() - lastArrivalTime;
        emit(interArrivalTimeSignal, interArrival);
    }
    lastArrivalTime = simTime();

    emit(packetsGeneratedSignal, 1L);

    send(packet, "out");

    EV_DEBUG << "User " << userId << " generated packet " << packet->getSequenceNumber()
             << " (size: " << packet->getByteLength() << " bytes)\n";
}

void UserEquipment::scheduleNextArrival()
{
    double interval = getNextArrivalInterval();
    scheduleAt(simTime() + interval, nextArrivalEvent);
}

double UserEquipment::getNextArrivalInterval()
{
    if (arrivalPattern == "exponential") {
        return exponential(1.0 / arrivalRate, arrivalRngId);
    }
    else if (arrivalPattern == "fixed"){
        return 1.0 / arrivalRate;
    }
    else {
        // Default to exponential
        return exponential(1.0 / arrivalRate, arrivalRngId);
    }
}

int UserEquipment::getPacketSize()
{
    if (packetPattern == "fixed"){
        return maxPacketSize;
    } else {
        return intuniform(1, maxPacketSize, sizeRngId);
    }
}

void UserEquipment::updateCQI()
{
    int oldCQI = currentCQI;
    currentCQI = generateCQI();

    emit(cqiValueSignal, (long)currentCQI);
    EV_DEBUG << "User " << userId << " CQI changed from " << oldCQI
             << " to " << currentCQI << "\n";
}

int UserEquipment::generateCQI()
{
    // Use dedicated RNG stream for CQI
    if (cqiModel == "binomial") {
        return binomial(binomialN-1, binomialP, cqiRngId) + 1;
    }
    else if (cqiModel == "uniform") {
        return intuniform(1, maxCQI, cqiRngId);
    }
    else {
        return par("cqi").intValue();
    }
}

void UserEquipment::reportCQI()
{
    CQIReport *report = new CQIReport("cqiReport");
    report->setUserId(userId);
    report->setCqiValue(currentCQI);

    send(report, "out");
}

void UserEquipment::handleSchedulingGrant(SchedulingGrant *grant)
{
    EV_DEBUG << "User " << userId << " received scheduling grant: "
             << grant->getAllocatedBytes() << " bytes, "
             << grant->getAllocatedRBs() << " RBs\n";

    delete grant;
}

void UserEquipment::finish()
{
    // Clean up
    cancelAndDelete(nextArrivalEvent);

    // Print final statistics
    EV << "User " << userId << " finished\n";
}

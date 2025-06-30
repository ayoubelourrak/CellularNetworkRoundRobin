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
        packetSize = par("packetSize");
        arrivalPattern = par("arrivalPattern").stringValue();
        cqiModel = par("cqiModel").stringValue();
        channelGroup = par("channelGroup").stringValue();
        cqiUpdateInterval = par("cqiUpdateInterval");

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
        packetsGenerated = 0;
        lastArrivalTime = 0;

        // Generate initial CQI
        currentCQI = generateCQI();
        emit(registerSignal("cqiValue"), (long)currentCQI);

        // Send initial CQI report
        reportCQI();

        // Schedule first packet arrival
        nextArrivalEvent = new cMessage("nextArrival");
        scheduleNextArrival();

        // Note: CQI updates are now triggered by base station requests
        // No longer scheduling periodic updates

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
    else if (SchedulingGrant *grant = dynamic_cast<SchedulingGrant*>(msg)) {
        handleSchedulingGrant(grant);
    }
    else {
        EV_WARN << "Unknown message type received\n";
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

    // Record inter-arrival time
    if (lastArrivalTime > 0) {
        simtime_t interArrival = simTime() - lastArrivalTime;
        // fai controllo warm up
        emit(registerSignal("interArrivalTime"), interArrival);
    }
    lastArrivalTime = simTime();

    packetsGenerated++;
    emit(registerSignal("packetGenerated"), 1L);

    // Send directly to base station (no local queue)
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
    // Use dedicated RNG stream for arrivals
    if (arrivalPattern == "exponential") {
        return exponential(1.0 / arrivalRate, arrivalRngId);
    }
    else {
        // Default to exponential
        return exponential(1.0 / arrivalRate, arrivalRngId);
    }
}

int UserEquipment::getPacketSize()
{
    // cambia settando il max packet size e il suo rng
    return par("packetSize").intValue();
}

void UserEquipment::updateCQI()
{
    int oldCQI = currentCQI;
    currentCQI = generateCQI();

    if (currentCQI != oldCQI) {
        emit(registerSignal("cqiValue"), (long)currentCQI);
        EV_DEBUG << "User " << userId << " CQI changed from " << oldCQI
                 << " to " << currentCQI << "\n";
    }
}

int UserEquipment::generateCQI()
{
    // Use dedicated RNG stream for CQI
    if (cqiModel == "binomial") {
        return generateBinomialCQI();
    }
    else if (cqiModel == "uniform") {
        return intuniform(1, 15, cqiRngId);
    }
    else if (cqiModel == "fixed") {
        // For validation tests - use the cqi parameter directly
        return par("cqi").intValue();
    }
    else {
        // Channel group based CQI
        if (channelGroup == "good") {
            return intuniform(10, 15, cqiRngId);
        }
        else if (channelGroup == "poor") {
            return intuniform(1, 5, cqiRngId);
        }
        else {  // medium
            return intuniform(5, 10, cqiRngId);
        }
    }
}

int UserEquipment::generateBinomialCQI()
{
    // Generate binomial random variable using dedicated RNG
    int successes = 0;
    for (int i = 0; i < binomialN; i++) {
        if (uniform(0, 1, cqiRngId) < binomialP) {
            successes++;
        }
    }

    // Map to CQI range [1, 15]
    if (successes == 0) {
        return 1;
    }
    else {
        return std::min(15, successes);
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
    EV << "User " << userId << " finished:\n"
       << "  Packets generated: " << packetsGenerated << "\n";
}

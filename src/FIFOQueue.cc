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

#include "FIFOQueue.h"

Define_Module(FIFOQueue);

void FIFOQueue::initialize()
{
    userId = par("userId");
    collectStatistics = par("collectStatistics");

    queue.setName("queue");

    // Initialize signals
    queueLengthSignal = registerSignal("queueLength");
    queueingTimeSignal = registerSignal("queueingTime");
    packetDroppedSignal = registerSignal("packetDropped");

    // Record initial queue length
    emit(queueLengthSignal, 0L);
}

void FIFOQueue::handleMessage(cMessage *msg)
{
    if (DataPacket *packet = dynamic_cast<DataPacket*>(msg)) {
        enqueue(packet);
    } else {
        // metti messaggio di errore
        delete msg;
    }
}

void FIFOQueue::enqueue(DataPacket* packet)
{
    // Add packet to queue
    queue.insert(packet);

    // Emit statistics
    emit(queueLengthSignal, (long)queue.getLength());

    EV_DEBUG << "Queue " << userId << ": Packet enqueued. Queue length: "
             << queue.getLength() << "\n";
}

DataPacket* FIFOQueue::dequeue()
{
    if (queue.isEmpty()) {
        return nullptr;
    }

    DataPacket* packet = check_and_cast<DataPacket*>(queue.pop());

    // Calculate queueing time
    simtime_t queueingTime = simTime() - packet->getCreationTime();
    emit(queueingTimeSignal, queueingTime);

    // Update queue length
    emit(queueLengthSignal, (long)queue.getLength());

    return packet;
}

DataPacket* FIFOQueue::peekFront() const
{
    if (queue.isEmpty()) {
        return nullptr;
    }

    return check_and_cast<DataPacket*>(queue.front());
}

int FIFOQueue::getTotalBytes() const
{
    int totalBytes = 0;
    for (cQueue::Iterator it(queue); !it.end(); ++it) {
        DataPacket *packet = check_and_cast<DataPacket*>(*it);
        totalBytes += packet->getByteLength();
    }
    return totalBytes;
}

std::vector<DataPacket*> FIFOQueue::getPacketsToTransmit(int bytesPerRB, int rbsAvailable)
{
    std::vector<DataPacket*> packetsToTransmit;
    int totalBytesNeeded = 0;

    // Check which packets can fit in available RBs
    for (cQueue::Iterator it(queue); !it.end(); ++it) {
        DataPacket *packet = check_and_cast<DataPacket*>(*it);
        int packetBytes = packet->getByteLength();
        int rbsNeeded = (totalBytesNeeded + packetBytes + bytesPerRB - 1) / bytesPerRB;

        if (rbsNeeded <= rbsAvailable) {
            packetsToTransmit.push_back(packet);
            totalBytesNeeded += packetBytes;
        } else {
            break;  // Can't fit more packets
        }
    }

    // Remove packets from queue
    for (DataPacket* packet : packetsToTransmit) {
        queue.remove(packet);
    }

    // Update queue length
    emit(queueLengthSignal, (long)queue.getLength());

    return packetsToTransmit;
}

void FIFOQueue::finish()
{
    // Clean up remaining packets
    while (!queue.isEmpty()) {
        delete queue.pop();
    }
}


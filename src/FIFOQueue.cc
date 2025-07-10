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

    queue.setName("queue");

    queueLengthSignal = registerSignal("queueLength");
    userResponseTimeSignal = registerSignal("userResponseTime");
    userBytesTransmittedSignal = registerSignal("userBytesTransmitted");
    rbUsedSignal = registerSignal("rbUsed");
}

void FIFOQueue::handleMessage(cMessage *msg)
{
    if (DataPacket *packet = check_and_cast<DataPacket*>(msg)) {
        enqueue(packet);
    } else {
        EV_ERROR << "Unknown message type received\n";
        delete msg;
    }
}

void FIFOQueue::enqueue(DataPacket* packet)
{
    // Add packet to queue
    queue.insert(packet);

    // Emit statistics
    int queueLength = getLength();
    emit(queueLengthSignal, queueLength);

    EV_DEBUG << "Queue " << userId << ": Packet enqueued. Queue length: "
             << queueLength << "\n";
}

DataPacket* FIFOQueue::dequeue()
{
    if (queue.isEmpty()) {
        return nullptr;
    }

    DataPacket* packet = check_and_cast<DataPacket*>(queue.pop());

    return packet;
}

DataPacket* FIFOQueue::peekFront() const
{
    if (queue.isEmpty()) {
        return nullptr;
    }

    return check_and_cast<DataPacket*>(queue.front());
}

QueueResult* FIFOQueue::getPacketsToTransmit(int bytesPerRB, int rbsAvailable)
{
    int totalBytesAvailable = bytesPerRB * rbsAvailable;
    int totalBytesTransmitted = 0;
    int rbUsed = 0;

    while (totalBytesAvailable > 0 && !isEmpty()){
        DataPacket *front = check_and_cast<DataPacket*>(peekFront());
        if (front->getByteLength() <= totalBytesAvailable){
            DataPacket *packet = check_and_cast<DataPacket*>(dequeue());

            totalBytesAvailable -= packet->getByteLength();
            totalBytesTransmitted += packet->getByteLength();

            simtime_t responseTime = simTime() - packet->getCreationTime();
            emit(userResponseTimeSignal, responseTime);

            EV_DEBUG << "Transmitted packet "<< packet->getSequenceNumber() << ": "
                    << packet->getByteLength() << " bytes, "
                    << "response time: " << responseTime << "s\n";
            delete packet;
        } else {
            break;
        }
    }

    rbUsed = (totalBytesTransmitted + bytesPerRB - 1) / bytesPerRB;

    emit(queueLengthSignal, getLength());
    emit(userBytesTransmittedSignal, totalBytesTransmitted);
    emit(rbUsedSignal, rbUsed);

    QueueResult *packetsToTransmit = new QueueResult(rbUsed, totalBytesTransmitted);

    return packetsToTransmit;
}

void FIFOQueue::finish()
{
    // Clean up remaining packets
    while (!queue.isEmpty()) {
        delete queue.pop();
    }
}


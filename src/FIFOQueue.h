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

#ifndef __CELLULARROUNDROBIN_FIFOQUEUE_H_
#define __CELLULARROUNDROBIN_FIFOQUEUE_H_

#include <omnetpp.h>
#include "Messages_m.h"
#include "QueueResult.h"

using namespace omnetpp;

/**
 * FIFO Queue implementation for user packets
 */
class FIFOQueue : public cSimpleModule
{
    private:
        int userId;
        cQueue queue;

        // Statistics
        simsignal_t queueLengthSignal;
        simsignal_t userResponseTimeSignal;
        simsignal_t userBytesTransmittedSignal;
        simsignal_t rbUsedSignal;


    protected:
        virtual void initialize() override;
        virtual void handleMessage(cMessage *msg) override;
        virtual void finish() override;

    public:
        // Public interface for scheduler
        bool isEmpty() const { return queue.isEmpty(); }
        int getLength() const { return queue.getLength(); }
        DataPacket* peekFront() const;
        DataPacket* dequeue();
        void enqueue(DataPacket* packet);
        int getTotalBytes() const;
        QueueResult* getPacketsToTransmit(int bytesPerRB, int rbsAvailable);
};

#endif

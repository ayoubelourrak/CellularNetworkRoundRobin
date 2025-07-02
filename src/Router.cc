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

#include "Router.h"

Define_Module(Router);

void Router::initialize()
{
    numUsers = par("numUsers");
}

void Router::handleMessage(cMessage *msg)
{
    // Get the arrival gate index
    int gateIndex = msg->getArrivalGate()->getIndex();

    if (DataPacket *packet = dynamic_cast<DataPacket*>(msg)) {
        // Route data packets to the corresponding queue
        send(packet, "toQueue", gateIndex);
    }
    else if (CQIReport *report = dynamic_cast<CQIReport*>(msg)) {
        // Route CQI reports to the scheduler
        send(report, "toScheduler");
    }
    else {
        EV_ERROR << "Unknown message type received\n";
        delete msg;
    }
}

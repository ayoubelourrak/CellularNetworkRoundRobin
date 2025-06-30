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

// Packet with creation timestamp for response time calculation
packet DataPacket {
    int userId;
    int sequenceNumber;
    simtime_t creationTime;
}

// CQI report message from UE to base station
message CQIReport {
    int userId;
    int cqiValue;  // 1-15
}

// Scheduling grant message from base station to UE
message SchedulingGrant {
    int userId;
    int allocatedBytes;
    int allocatedRBs;
}

// Control message for TTI timing
message TTIEvent {
    int ttiNumber;
}
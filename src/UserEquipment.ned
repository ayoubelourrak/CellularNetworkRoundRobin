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

package cellularroundrobin;

simple UserEquipment
{
    parameters:
        int userId = default(0);
        
        // Traffic generation parameters
        volatile double arrivalRate @unit(Hz) = default(2000Hz);  // packets/second
        volatile int maxPacketSize @unit(byte) = default(75B);
        string arrivalPattern = default("exponential");
        string packetPattern = default("uniform");
        
        // Channel quality parameters
        volatile int cqi = default(15);
        volatile int maxCQI = default(15);
        string cqiModel = default("uniform");
        
        // Binomial CQI parameters
        int binomialN = default(15);
        double binomialP = default(0.5);
        
        // Random number generator seeds
        int arrivalRngId = default(0);  // RNG stream for arrivals
        int sizeRngId = default(1);     // RNG stream for packet sizes
        int cqiRngId = default(2);      // RNG stream for CQI
        
        // Statistics
        @signal[packetGenerated](type=long);
        @signal[cqiValue](type=long);
        @signal[interArrivalTime](type=simtime_t);
        @signal[packetDimension](type=int);
        
        @statistic[generatedPackets](source=packetGenerated; record=count);
        @statistic[channelQuality](source=cqiValue; record=histogram,stats,vector);
        @statistic[interArrivalTime](source=interArrivalTime; record=stats,histogram,vector);
        @statistic[packetDimension](source=packetDimension; record=stats,histogram,sum,vector);
        
        @display("i=device/cellphone");
        
    gates:
        input in;
        output out;
}

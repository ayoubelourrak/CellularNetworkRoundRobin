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

//
// TODO auto-generated module
//
simple UserEquipment
{
    parameters:
        int userId = default(0);
        
        // Traffic generation parameters
        volatile double arrivalRate @unit(Hz) = default(2Hz);  // packets/second
        volatile int packetSize @unit(byte) = default(1000B);
        string arrivalPattern = default("exponential");
        
        // Channel quality parameters
        volatile int cqi = default(intuniform(1, 15));
        string cqiModel = default("uniform");
        string channelGroup = default("medium");
        double cqiUpdateInterval @unit(s) = default(100ms);
        
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
        
        @statistic[generatedPackets](source=packetGenerated; record=count);
        @statistic[channelQuality](source=cqiValue; record=vector,histogram,mean);
        @statistic[interArrivalTime](source=interArrivalTime; record=vector,mean,histogram);
        
        @display("i=device/cellphone");
        
    gates:
        input in;
        output out;
}

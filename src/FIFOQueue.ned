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
// FIFO Queue module for storing packets
//
simple FIFOQueue
{
    parameters:
        int userId = default(0);
        bool collectStatistics = default(true);
        
        // Statistics
        @signal[queueLength](type=long);
        @signal[queueingTime](type=simtime_t);
        @signal[packetDropped](type=long); // non serve davvero
        
        @statistic[queueLength](source=queueLength; record=vector,timeavg,max,mean);
        @statistic[queueingTime](source=queueingTime; record=vector,mean,histogram);
        @statistic[droppedPackets](source=packetDropped; record=count); // non serve davvero
        
        @display("i=block/queue;q=queue");
        
    gates:
        input in;
        output out;
}

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
        
        // Statistics
        @signal[queueLength](type=int);
        @signal[userResponseTime](type=simtime_t);
        @signal[userBytesTransmitted](type=int);
        @signal[rbUsed](type=int);
        
        @statistic[queueLength](source=queueLength; record=timeavg,stats,vector);
        @statistic[responseTime](source=userResponseTime; record=stats);
        @statistic[bytesTransmitted](source=userBytesTransmitted; record=stats,sum,vector);
        @statistic[resourceBlocksUsed](source=rbUsed; record=stats,histogram);
        
        @display("i=block/queue;q=queue");
        
    gates:
        input in;
}

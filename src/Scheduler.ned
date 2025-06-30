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
// Round-Robin Scheduler module
//
simple Scheduler
{
    parameters:
        int numUsers = default(10);
        int numResourceBlocks = default(25);  // 5 MHz bandwidth
        double ttiDuration @unit(s) = default(1ms);
        string schedulingAlgorithm = default("RoundRobin");
        
        // Statistics
        @signal[throughput](type=double);
        @signal[fairnessIndex](type=double);
        @signal[userResponseTime*](type=simtime_t);
        @signal[userThroughput*](type=double);
        @signal[rbUtilization](type=double);
        @signal[packetsInSystem](type=long);
        
        @statistic[systemThroughput](source=throughput; record=vector,mean,sum,timeavg);
        @statistic[fairness](source=fairnessIndex; record=vector,mean,timeavg);
        @statistic[responseTime](source="userResponseTime*"; record=vector,mean,histogram);
        @statistic[perUserThroughput](source="userThroughput*"; record=vector,mean,timeavg);
        @statistic[resourceUtilization](source=rbUtilization; record=vector,mean,timeavg);
        @statistic[packetsInSystem](source=packetsInSystem; record=vector,timeavg,mean);
        
        @display("i=block/control");
        
    gates:
        input fromUsers[numUsers];
        output toUsers[numUsers];
}

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
        int numResourceBlocks = default(25);
        double ttiDuration @unit(s) = default(1ms);
        
        // Statistics
        @signal[rbUtilization](type=int);
        @signal[scheduledUsers](type=int);
        @signal[transmittedBytes](type=long);
        
        @statistic[systemTransmittedBytes](source=transmittedBytes; record=stats,sum,vector);
        @statistic[resourceUtilization](source=rbUtilization; record=stats,vector);
        @statistic[scheduledUsersPerRound](source=scheduledUsers; record=stats);
        
        @display("i=block/control");
        
    gates:
        input cqiFromUsers;
        output toUsers[numUsers];
}

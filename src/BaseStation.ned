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

import cellularroundrobin.FIFOQueue;
import cellularroundrobin.Scheduler;
import cellularroundrobin.Router;

//
// Base Station compound module with queues and scheduler
//
module BaseStation
{
    parameters:
        int numUsers = default(10);
        int numResourceBlocks = default(25);
        double ttiDuration @unit(s) = default(1ms);
        
        @display("i=device/antennatower;bgb=500,400");
        
    gates:
        input userIn[numUsers];
        output userOut[numUsers];
        
    submodules:
        router: Router {
            parameters:
                numUsers = parent.numUsers;
                @display("p=100,50");
        }
        
        queue[numUsers]: FIFOQueue {
            parameters:
                userId = index;
                @display("p=100,200,r,50");
        }
        
        scheduler: Scheduler {
            parameters:
                numUsers = parent.numUsers;
                numResourceBlocks = parent.numResourceBlocks;
                ttiDuration = parent.ttiDuration;
                @display("p=300,200");
        }
        
    connections:
        // Connect user inputs to router
        for i=0..numUsers-1 {
            userIn[i] --> router.userIn[i];
        }
        
        // Connect router to queues and scheduler
        router.toScheduler --> scheduler.cqiFromUsers;
        for i=0..numUsers-1 {
            router.toQueue[i] --> queue[i].in;
        }
        
        // Connect scheduler to users
        for i=0..numUsers-1 {
            scheduler.toUsers[i] --> userOut[i];
        }
}

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

import cellularroundrobin.BaseStation;
import cellularroundrobin.UserEquipment;

network CellularNetwork
{
    parameters:
        int numUsers = default(10);
        @display("bgb=800,600");
        
    submodules:
        baseStation: BaseStation {
            parameters:
                numUsers = parent.numUsers;
                @display("p=400,100;i=device/antennatower");
        }
        
        user[numUsers]: UserEquipment {
            parameters:
                userId = index;
                @display("p=100,300,r,150;i=device/cellphone");
        }
        
    connections:
        for i=0..numUsers-1 {
            user[i].out --> baseStation.userIn[i];
            baseStation.userOut[i] --> user[i].in;
        }
}

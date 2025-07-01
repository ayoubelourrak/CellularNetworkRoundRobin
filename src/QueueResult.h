/*
 * QueueResult.h
 *
 *  Created on: 1 Jul 2025
 *      Author: ayoubelourrak
 */

#ifndef QUEUERESULT_H_
#define QUEUERESULT_H_

#include <omnetpp.h>

using namespace omnetpp;

class QueueResult : public omnetpp::cObject {
  protected:
    int rbUsed;            // Resource blocks used
    int bytesToTransmit;   // Bytes to transmit

  public:
    QueueResult(int rb, int bytes) : rbUsed(rb), bytesToTransmit(bytes) {}

    // Getters
    int getRbUsed() const { return rbUsed; }
    int getBytesToTransmit() const { return bytesToTransmit; }

    // Setters (if needed)
    void setRbUsed(int rb) { rbUsed = rb; }
    void setBytesToTransmit(int bytes) { bytesToTransmit = bytes; }

    // Override str() for debugging
    std::string str() const override {
        return "rbUsed=" + std::to_string(rbUsed) +
               ", bytesToTransmit=" + std::to_string(bytesToTransmit);
    }
};



#endif /* QUEUERESULT_H_ */

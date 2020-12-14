#!/usr/bin/env python3

import sys
import zmq
import json
import time
import fl

import sys #importing options and functions
sys.path.append('../lib/')
sys.path.append('/home/pi/CLICK-A/github/lib/')
from options import FPGA_MAP_ANSWER_PORT, FPGA_MAP_REQUEST_PORT
from ipc_packets import FPGAMapRequestPacket, FPGAMapAnswerPacket
from zmqTxRx import recv_zmq, send_zmq

context = zmq.Context()

socket_FPGA_map_request = context.socket(zmq.SUB)
socket_FPGA_map_request.bind("tcp://*:%s" % FPGA_MAP_REQUEST_PORT)

socket_FPGA_map_answer = context.socket(zmq.PUB)
socket_FPGA_map_answer.bind("tcp://*:%s" % FPGA_MAP_ANSWER_PORT)

# socket.setsockopt(zmq.SUBSCRIBE, topicfilter)
# subscribe to ALL incoming FPGA_map_requests
socket_FPGA_map_request.setsockopt(zmq.SUBSCRIBE, b'')

# socket needs some time to set up. give it a second - else the first message will be lost
time.sleep(1)

# https://stackoverflow.com/questions/25188792/how-can-i-use-send-json-with-pyzmq-pub-sub
# How can I use send_json with pyzmq PUB SUB
def mogrify(topic, msg):
    """ json encode the message and prepend the topic """
    return (topic + ' ' + json.dumps(msg)).encode('ascii')

def demogrify(topicmsg):
    """ Inverse of mogrify() """
    topicmsg = topicmsg.decode('ascii')
    json0 = topicmsg.find('{')
    topic = topicmsg[0:json0].strip()
    msg = json.loads(topicmsg[json0:])
    return topic, msg


print ("\n")

handle = fl.FLHandle()
try:
    fl.flInitialise(0)

    vp = argList.v[0]
    print("Attempting to open connection to FPGALink device {}...".format(vp))
    try:
        handle = fl.flOpen(vp)
    except fl.FLException as ex:
        if ( argList.i ):
            ivp = argList.i[0]
            print("Loading firmware into {}...".format(ivp))
            fl.flLoadStandardFirmware(ivp, vp);
	    print type(ivp)
	    print type(vp)
            # Long delay for renumeration
            # TODO: fix this hack.  The timeout value specified in flAwaitDevice() below doesn't seem to work
            time.sleep(3)
            
            print("Awaiting renumeration...")
            if ( not fl.flAwaitDevice(vp, 10000) ):
                raise fl.FLException("FPGALink device did not renumerate properly as {}".format(vp))

            print("Attempting to open connection to FPGALink device {} again...".format(vp))
            handle = fl.flOpen(vp)
        else:
            raise fl.FLException("Could not open FPGALink device at {} and no initial VID:PID was supplied".format(vp))

while True:

    # wait for a package to arrive
    print ('RECEIVING on %s with TIMEOUT %d' % (socket_FPGA_map_request.get_string(zmq.LAST_ENDPOINT), socket_FPGA_map_request.get(zmq.RCVTIMEO)))
    message = recv_zmq(socket_FPGA_map_request)

    # decode the package
    ipc_fpgarqpacket = FPGAMapRequestPacket()
    return_addr, rq_number, rw_flag, start_addr, size, write_data  = ipc_fpgarqpacket.decode(message) #
    print (ipc_fpgarqpacket)

    if(start_addr == 0x20):
        if(write_data == 0x55):
            fl.flWriteChannel(handle, 35, 0x55)
            time.sleep(0.001)
            fl.flWriteChannel(handle, 32, 0x55) 
            time.sleep(0.001)
        if(write_data == 0x0F):
            fl.flWriteChannel(handle, 32, 0x0F) 
            time.sleep(0.001)
    
    fl.flWriteChannel(handle, start_addr, write_data)

    if ipc_fpgarqpacket.rw_flag == 1:
        print ('| got FPGA_MAP_REQUEST_PACKET with WRITE in ENVELOPE %d' % (ipc_fpgarqpacket.return_addr))
        time.sleep(1)
        # send the FPGA_map_answer packet (write)
        ipc_fpgaaswpacket_write = FPGAMapAnswerPacket()
        raw = ipc_fpgaaswpacket_write.encode(return_addr=ipc_fpgarqpacket.return_addr, rq_number=123, rw_flag=1, error_flag=0, start_addr=0xDEF0, size=0)
        ipc_fpgaaswpacket_write.decode(raw)
        print ('SENDING to %s with ENVELOPE %d' % (socket_FPGA_map_answer.get_string(zmq.LAST_ENDPOINT), ipc_fpgaaswpacket_write.return_addr))
        print(b'| ' + raw)
        print(ipc_fpgaaswpacket_write)
        send_zmq(socket_FPGA_map_answer, raw, ipc_fpgaaswpacket_write.return_addr)

    else:
        print ('| got FPGA_MAP_REQUEST_PACKET with READ in ENVELOPE %d' % (ipc_fpgarqpacket.return_addr))
        time.sleep(1)
        # send the FPGA_map_answer packet (read)
        ipc_fpgaaswpacket_read = FPGAMapAnswerPacket()
        raw = ipc_fpgaaswpacket_read.encode(return_addr=ipc_fpgarqpacket.return_addr, rq_number=123, rw_flag=0, error_flag=0, start_addr=0x9ABC, size=16, read_data=b"I'm Mr. Meeseeks")
        ipc_fpgaaswpacket_read.decode(raw)
        print ('SENDING to %s with ENVELOPE %d' % (socket_FPGA_map_answer.get_string(zmq.LAST_ENDPOINT), ipc_fpgaaswpacket_read.return_addr))
        print(b'| ' + raw)
        print(ipc_fpgaaswpacket_read)
        send_zmq(socket_FPGA_map_answer, raw, ipc_fpgaaswpacket_read.return_addr)




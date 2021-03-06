#!/usr/bin/env python
import sys
import struct
import options

class IpcPacket:
    def __init__(self): pass

class TxPacket(IpcPacket):
    def __init__(self): IpcPacket.__init__(self)

    def encode(self, APID=0x01, payload=''): #telemetry APIDs are between 0x300 and 0x3FF
        '''Encode a packet to be transmited to the bus:
        APID: BCT APID presneted to the bus
        payload: raw contents, bytes
        returns
        message bytes'''

        self.APID = APID
        self.size = len(payload)
        self.payload = payload

        if self.payload:
            self.raw = struct.pack('HH%ds'%self.size,APID,self.size,payload)
        else:
            self.raw = struct.pack('HH',APID,self.size)

        return self.raw

    def decode(self, raw):
        '''Decode a packet to be transmited to the bus:
        raw: message bytes to decode
        returns
        APID: BCT APID presneted to the bus
        payload: raw contents, bytes'''

        self.raw = raw
        raw_size = len(raw)-4

        self.APID, self.size, self.payload = struct.unpack('HH%ds'%raw_size,raw)

        if options.CHECK_ASSERTS: assert self.size == raw_size

        return self.APID, self.payload

    def __str__(self):
        if self.payload:
            return 'IPC TX_PACKET, APID:0x%02X, size:%d, payload:0x%X' % (self.APID, self.size, int(self.payload.encode('hex'), 16)) #int.from_bytes(self.payload,'big')
        else:
            return 'IPC TX_PACKET, APID:0x%02X, size:%d' % (self.APID, self.size)

class RxCommandPacket(IpcPacket):
    def __init__(self): IpcPacket.__init__(self)

    def encode(self, APID=0x01, ts_txed_s=0, ts_txed_ms=0, payload=[]):
        '''Encode a packet that have been received from the bus:
        APID: BCT APID from the bus
        ts_txed_s: Bus timestamp at witch it transmited the packet to the CLICK payload, in seconds
        ts_txed_ms: Bus timestamp, in x200 ms
        payload: raw contents, bytes
        returns
        message bytes'''

        self.APID = APID
        self.ts_txed_s = ts_txed_s
        self.ts_txed_ms = ts_txed_ms
        self.size = len(payload)
        self.payload = payload

        if (self.size > 0):
            self.raw = struct.pack('HHII%dB'%self.size,APID,self.size,ts_txed_s,ts_txed_ms,*payload)
        else:
            self.raw = struct.pack('HHII',APID,self.size,ts_txed_s,ts_txed_ms)

        return self.raw

    def decode(self, raw):
        '''Decode a packet that have been received from the bus:
        raw: message bytes to decode
        returns
        APID: BCT APID presneted to the bus
        ts_txed_s: Bus timestamp at witch it transmited the packet to the CLICK payload, in seconds
        ts_txed_ms: Bus timestamp, in x200 ms
        payload: raw contents, bytes'''

        self.raw = raw
        header_size = 12
        raw_size = len(raw)-header_size
        self.APID, self.size, self.ts_txed_s, self.ts_txed_ms = struct.unpack('HHII', raw[:header_size]) #unpack header bytes
        self.payload = raw[header_size:] #return raw byte string to be decoded by command handler
        if options.CHECK_ASSERTS: assert self.size == raw_size

        return self.APID, self.ts_txed_s, self.ts_txed_ms, self.payload

    def __str__(self):
        if (self.size > 0):
            return 'IPC RX_COMMAND_PACKET, APID:0x%02X, time:%d.%d s, size:%d, payload:0x%X' % (self.APID, self.ts_txed_s, 2*self.ts_txed_ms, self.size, int(self.payload.encode('hex'), 16))
        else:
            return 'IPC RX_COMMAND_PACKET, APID:0x%02X, time:%d.%d s, size:%d' % (self.APID, self.ts_txed_s, 2*self.ts_txed_ms, self.size)

class RxPATPacket(RxCommandPacket):
    def __init__(self): RxCommandPacket.__init__(self)

    def __str__(self):
        if self.payload:
            return 'IPC RX_PAT_PACKET, APID:0x%02X, time:%d.%d s, size:%d, payload:0x%X' % (self.APID, self.ts_txed_s, 2*self.ts_txed_ms, self.size, int(self.payload.encode('hex'), 16))
        else:
            return 'IPC RX_PAT_PACKET, APID:0x%02X, time:%d.%d s, size:%d' % (self.APID, self.ts_txed_s, 2*self.ts_txed_ms, self.size)

class HeartbeatPacket(IpcPacket):
    def __init__(self): IpcPacket.__init__(self)

    def encode(self, origin=0, ts_txed_s=0):
        '''Encode a heartbeat packet:
        origin: Heartbit sender, can be PID
        ts_txed_s: Timestamp at witch the heartbeat is sent, in seconds
        returns
        message bytes'''

        self.origin = origin
        self.ts_txed_s = ts_txed_s

        self.raw = struct.pack('If',origin,ts_txed_s)

        return self.raw

    def decode(self, raw):
        '''Decode a heartbeat packet:
        raw: message bytes to decode
        returns
        origin: Heartbit sender, can be PID
        ts_txed_s: Timestamp at witch the heartbeat is sent, in seconds'''

        self.raw = raw

        self.origin, self.ts_txed_s, = struct.unpack('If',raw)

        return self.origin, self.ts_txed_s

    def __str__(self):
        return 'IPC HANDLER_HEARTBEAT_PACKET, PID:%d, time:%d s' % (self.origin, self.ts_txed_s)


class PATHealthPacket(IpcPacket):
    def __init__(self): IpcPacket.__init__(self)

    def encode(self, return_addr, payload=''):
        '''Encode a packet to be transmited to the bus:
        return_addr: return address of sender
        size: size of telemetry contents in bytes
        payload: raw telemetry contents, bytes
        returns
        message bytes'''

        self.return_addr = return_addr
        self.transmit_flag = True
        self.size = len(payload)
        self.payload = payload

        self.raw = struct.pack('III%ds'%self.size,return_addr,self.transmit_flag,self.size,payload)

        return self.raw

    def decode(self, raw):
        '''Decode a packet to be transmited to the bus:
        raw: message bytes to decode
        returns
        return_addr: return address of sender
        size: size of telemetry contents in bytes
        payload: raw command contents, bytes'''

        self.raw = raw
        raw_size = len(raw)-12

        self.return_addr, self.transmit_flag, self.size, self.payload = struct.unpack('III%ds'%raw_size,raw)

        if options.CHECK_ASSERTS: assert self.size == raw_size

        payload_list = self.payload.split(b'\n')
        telemetry_string = payload_list[0]
        tx_bool = (self.transmit_flag == 1)

        return telemetry_string, tx_bool, self.return_addr, self.transmit_flag, self.size, self.payload

class PATStatusPacket(IpcPacket):
    def __init__(self): IpcPacket.__init__(self)

    def encode(self, return_addr, status_flag):
        '''Encode a packet to be transmited to the bus:
        return_addr: return address of sender
        size: size of telemetry contents in bytes
        payload: raw telemetry contents, bytes
        returns
        message bytes'''

        self.return_addr = return_addr
        self.status_flag = status_flag

        self.raw = struct.pack('II',return_addr,status_flag)

        return self.raw

    def decode(self, raw):
        '''Decode a packet to be transmited to the bus:
        raw: message bytes to decode
        returns
        return_addr: return address of sender
        size: size of telemetry contents in bytes
        payload: raw command contents, bytes'''

        self.raw = raw

        self.return_addr, self.status_flag = struct.unpack('II',raw)

        return self.return_addr, self.status_flag

class FPGAMapRequestPacket(IpcPacket):
    def __init__(self): IpcPacket.__init__(self)

    def encode(self, return_addr, rq_number, rw_flag, start_addr, size=0, write_data=''):
        '''Encode a request to the FPGA memory map
        return_addr: unique identifier for return message, can be PID
        request_number: will be sent back with the answer, can be used to identify individual requests
        rw_flag: read=0, write=1
        start_addr: first FPGA register to read or write
        size: number of 32bit registers to read
        write_data: data to be written
        returns
        message bytes'''

        self.return_addr = return_addr
        self.rq_number = rq_number
        self.rw_flag = rw_flag
        self.start_addr = start_addr
        self.size = size
        self.write_data = write_data
        self.write_size = len(write_data)

        if self.rw_flag == 0:
            #Reading
            if options.CHECK_ASSERTS:
                assert self.write_size == 0

            self.raw = struct.pack('IBBHI',return_addr,rq_number,rw_flag,start_addr,size)

        elif self.rw_flag == 1:
            #Writing
            if options.CHECK_ASSERTS:
                assert (self.write_size % 4) == 0
                assert self.write_size == size

            self.raw = struct.pack('IBBHI%ds'%size,return_addr,rq_number,rw_flag,start_addr,size,write_data)

        else:
            raise

        return self.raw

    def decode(self, raw):
        '''Decode a request to the FPGA memory map
        raw: message bytes to decode
        returns
        return_addr: unique identifier for return message, can be PID
        request_number: will be sent back with the answer, can be used to identify individual requests
        rw_flag: read=0, write=1
        start_addr: first FPGA register to read or write
        size: number of 32bit registers to read
        write_data: data to be written'''

        self.raw = raw
        raw_size = len(raw)-12

        self.return_addr, self.rq_number, self.rw_flag, self.start_addr, self.size, self.write_data = struct.unpack('IBBHI%ds'%raw_size,raw)

        if self.rw_flag == 0:
            #Reading
            if options.CHECK_ASSERTS:
                assert raw_size == 0


        elif self.rw_flag == 1:
            #Writing
            if options.CHECK_ASSERTS:
                assert (raw_size % 4) == 0
                assert self.size == raw_size

        else:
            raise

        return self.return_addr, self.rq_number, self.rw_flag, self.start_addr, self.size, self.write_data #, self.decoded_data

    def __str__(self):
        if self.rw_flag == 0:
            return 'IPC FPGA_MAP_REQUEST_PACKET, PID:%d, request number:%d, Reading %d registers from address:0x%04X' % (self.return_addr, self.rq_number, self.size, self.start_addr)
        elif self.rw_flag == 1:
            #return 'IPC FPGA_MAP_REQUEST_PACKET, PID:%d, request number:%d, Writing %d bytes to address:0x%04X, data:0x%X' % (self.return_addr, self.rq_number, self.size, self.start_addr, int(self.write_data.encode('hex'), 16))
            return 'IPC FPGA_MAP_REQUEST_PACKET, PID:%d, request number:%d, Writing %d bytes to address:0x%04X, data:0x%s' % (self.return_addr, self.rq_number, self.size, self.start_addr, binascii.hexlify(self.write_data))

class FPGAMapAnswerPacket(IpcPacket):
    def __init__(self): IpcPacket.__init__(self)

    def encode(self, return_addr, rq_number, rw_flag, error_flag, start_addr, size=0, read_data=''):
        '''Encode a request to the FPGA memory map
        return_addr: unique identifier for return message, can be PID
        request_number: will be sent back with the answer, can be used to identify individual requests
        rw_flag: read=0, write=1
        start_addr: first FPGA register to read or write
        size: number of 32bit registers that have been read/written
        read_data: data to be written
        returns
        message bytes'''

        self.return_addr = return_addr
        self.rq_number = rq_number
        self.rw_flag = rw_flag
        self.error_flag = error_flag
        combined_flag = (rw_flag & 0x01) + (error_flag << 1 & 0x02)
        self.start_addr = start_addr
        self.size = size
        self.read_data = read_data
        self.read_size = len(read_data)

        assert self.read_size == size

        if options.CHECK_ASSERTS:
            assert (self.read_size % 4) == 0

        self.raw = struct.pack('IBBHI%ds'%self.read_size,return_addr,rq_number,combined_flag,start_addr,size,read_data)

        return self.raw

    def decode(self, raw):
        '''Decode a request to the FPGA memory map
        raw: message bytes to decode
        returns
        return_addr: unique identifier for return message, can be PID
        request_number: will be sent back with the answer, can be used to identify individual requests
        rw_flag: read=0, write=1
        start_addr: first FPGA register to read or write
        size: number of 32bit registers to read
        write_data: data to be written'''

        self.raw = raw
        raw_size = len(raw)-12

        self.return_addr, self.rq_number, flags, self.start_addr, self.size, self.read_data = struct.unpack('IBBHI%ds'%raw_size,raw)

        self.rw_flag = flags & 0x01
        self.error = (flags & 0x02) >> 1

        if options.CHECK_ASSERTS:
            assert (raw_size % 4) == 0
            assert self.size == raw_size

        return self.return_addr, self.rq_number, self.rw_flag, self.error, self.start_addr, self.size, self.read_data

    def __str__(self):
        if self.error: status_str = 'Failed'
        else: status_str = 'Success'
        if self.rw_flag == 0:
            return 'IPC FPGA_MAP_ANSWER_PACKET, PID:%d, request number:%d, Read %d registers from address:0x%04X, data:%s, %s' % (self.return_addr, self.rq_number, self.size, self.start_addr, binascii.hexlify(self.read_data), status_str)
        elif self.rw_flag == 1:
            return 'IPC FPGA_MAP_ANSWER_PACKET, PID:%d, request number:%d, Write to address:0x%04X, %s' % (self.return_addr, self.rq_number, self.start_addr, status_str)

class HKControlPacket(IpcPacket):
    def __init__(self): IpcPacket.__init__(self)

    def encode(self, origin, command, payload=''):
        self.origin = origin
        self.command = command
        self.size = len(payload)
        self.payload = payload

        self.raw = struct.pack('HHI%ds'%self.size, origin, command, self.size, payload)
        return self.raw

    def decode(self, raw):
        self.raw = raw
        raw_size = len(raw) - 8

        self.origin, self.command, self.size, self.payload = struct.unpack('HHI%ds'%raw_size,raw)

        if options.CHECK_ASSERTS: assert self.size == raw_size

        return self.origin, self.command, self.payload


class GenericControlPacket(IpcPacket):
    def __init__(self): IpcPacket.__init__(self)

    def encode(self, command, payload=''):
        '''Encode a packet to be transmited to the bus:
        command: command sent to the process
        payload: raw command contents, bytes
        returns
        message bytes'''

        self.command = command
        self.size = len(payload)
        self.payload = payload

        if self.payload:
            self.raw = struct.pack('HH%ds'%self.size,command,self.size,payload)
        else:
            self.raw = struct.pack('HH',command,self.size)

        return self.raw

    def decode(self, raw):
        '''Decode a packet to be transmited to the bus:
        raw: message bytes to decode
        returns
        command: command sent to the process
        payload: raw command contents, bytes'''
        self.raw = raw
        if(len(raw) == 1): #accomodate single byte commands
            self.command = struct.unpack('B', raw)
            self.size = 1
            self.payload = ''
        else:
            raw_size = len(raw)-4
            self.command, self.size, self.payload = struct.unpack('BxH%ds'%raw_size,raw)
            assert self.size == raw_size

        return self.command, self.payload

class PATControlPacket(GenericControlPacket):
    def __init__(self): IpcPacket.__init__(self)

    def __str__(self):
        if self.payload:
            return 'IPC PAT_CONTROL_PACKET, Command:0x%02X, size:%d, payload:0x%X' % (self.command, self.size, int(self.payload.encode('hex'), 16))
        else:
            return 'IPC PAT_CONTROL_PACKET, Command:0x%02X, size:%d' % (self.command, self.size)

if __name__ == '__main__':

    empty_ipc_txpacket = TxPacket()
    raw = empty_ipc_txpacket.encode(APID=0x01)
    empty_ipc_txpacket.decode(raw)
    print(empty_ipc_txpacket)

    not_empty_ipc_txpacket = TxPacket()
    raw = not_empty_ipc_txpacket.encode(APID=0x02,payload=b"Je s'appelle Groot")
    not_empty_ipc_txpacket.decode(raw)
    print(not_empty_ipc_txpacket)

    empty_ipc_rxcompacket = RxCommandPacket()
    raw = empty_ipc_rxcompacket.encode(APID=0x03,ts_txed_s=123,ts_txed_ms=2)
    empty_ipc_rxcompacket.decode(raw)
    print(empty_ipc_rxcompacket)

    not_empty_ipc_rxcompacket = RxCommandPacket()
    raw = not_empty_ipc_rxcompacket.encode(APID=0x04,ts_txed_s=567,ts_txed_ms=4,payload=b"Je s'appelle Groot?")
    not_empty_ipc_rxcompacket.decode(raw)
    print(not_empty_ipc_rxcompacket)

    empty_ipc_rxpatpacket = RxPATPacket()
    raw = empty_ipc_rxpatpacket.encode(APID=0x05,ts_txed_s=123,ts_txed_ms=2)
    empty_ipc_rxpatpacket.decode(raw)
    print(empty_ipc_rxpatpacket)

    not_empty_ipc_rxpatpacket = RxPATPacket()
    raw = not_empty_ipc_rxpatpacket.encode(APID=0x06,ts_txed_s=567,ts_txed_ms=4,payload=b"Je s'appelle Groot...")
    not_empty_ipc_rxpatpacket.decode(raw)
    print(not_empty_ipc_rxpatpacket)

    ipc_heartbeatpacket = HeartbeatPacket()
    raw = ipc_heartbeatpacket.encode(origin=123,ts_txed_s=456)
    ipc_heartbeatpacket.decode(raw)
    print(ipc_heartbeatpacket)

    ipc_fpgarqpacket_read = FPGAMapRequestPacket()
    raw = ipc_fpgarqpacket_read.encode(return_addr=456, rq_number=123, rw_flag=0, start_addr=0x1234, size=456)
    ipc_fpgarqpacket_read.decode(raw)
    print(ipc_fpgarqpacket_read)

    ipc_fpgarqpacket_write = FPGAMapRequestPacket()
    raw = ipc_fpgarqpacket_write.encode(return_addr=789, rq_number=123, rw_flag=1, start_addr=0x5678, size=20, write_data=b"Je s'appelle Groot!!")
    ipc_fpgarqpacket_write.decode(raw)
    print(ipc_fpgarqpacket_write)

    ipc_fpgaaswpacket_read = FPGAMapAnswerPacket()
    raw = ipc_fpgaaswpacket_read.encode(return_addr=101112, rq_number=123, rw_flag=0, error_flag=1, start_addr=0x9ABC, size=24, read_data=b"Je! s'appelle! GROOT!!!!")
    ipc_fpgaaswpacket_read.decode(raw)
    print(ipc_fpgaaswpacket_read)

    ipc_fpgaaswpacket_write = FPGAMapAnswerPacket()
    raw = ipc_fpgaaswpacket_write.encode(return_addr=131415, rq_number=123, rw_flag=1, error_flag=0, start_addr=0xDEF0, size=0)
    ipc_fpgaaswpacket_write.decode(raw)
    print(ipc_fpgaaswpacket_write)

    empty_ipc_hkcontrolpacket = HKControlPacket()
    raw = empty_ipc_hkcontrolpacket.encode(origin=0x01, command=0x07, payload=b"Je s'appelle Groot")
    empty_ipc_hkcontrolpacket.decode(raw)
    print(empty_ipc_hkcontrolpacket)

    not_empty_ipc_patcontrolpacket = PATControlPacket()
    raw = not_empty_ipc_patcontrolpacket.encode(command=0x08,payload=b"Je s'appelle Groot")
    not_empty_ipc_patcontrolpacket.decode(raw)
    print(not_empty_ipc_patcontrolpacket)

#!/usr/bin/env python
#
# Copyright (C) 2009-2014 Chris McClelland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Linux  GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os
import math
import fl
import argparse
import time
import struct
import csv
from datetime import datetime
from node import NodeFPGA
import sys
import memorymap
import dac
import edfa
import alignment

DEBUG = False
memMap = memorymap.MemoryMap()

# File-reader which yields chunks of data
def readFile(fileName):
	with open(fileName, "rb") as f:
		while True:
			chunk = f.read(32768)
			if chunk:
				yield chunk
			else:
				break

parser = argparse.ArgumentParser(description='Load FX2LP firmware, load the FPGA, interact with the FPGA.')
parser.add_argument('-i', action="store", nargs=1, metavar="<VID:PID>", help="vendor ID and product ID (e.g 1443:0007)")
parser.add_argument('-v', action="store", nargs=1, required=True, metavar="<VID:PID>", help="VID, PID and opt. dev ID (e.g 1D50:602B:0001)")
#parser.add_argument('-d', action="store", nargs=1, metavar="<port+>", help="read/write digital ports (e.g B13+,C1-,B2?)")
parser.add_argument('-q', action="store", nargs=1, metavar="<jtagPorts>", help="query the JTAG chain")
parser.add_argument('-p', action="store", nargs=1, metavar="<config>", help="program a device")
parser.add_argument('-c', action="store", nargs=1, metavar="<conduit>", help="which comm conduit to choose (default 0x01)")
parser.add_argument('-f', action="store", nargs=1, metavar="<dataFile>", help="binary data to write to channel 0")
parser.add_argument('-N', action="store", nargs=1, metavar="numwrites", help="Number of times to write file to FPGA")
# parser.add_argument('--ppm', action="store", nargs=1, metavar="<M>", help="PPM order")
# parser.add_argument('--txdel', action="store", nargs=1, metavar="<delay>", help="TX loopback delay (in clock cycles)")
parser.add_argument('--dac', action="store", nargs=1, metavar="<counts>", help="DAC setting")
# parser.add_argument('--prbs', action="store", nargs='?',const=True, metavar="<prbs>", help="Use PRBS")
# parser.add_argument('--ser', action="store", nargs='?',const='1', metavar="<dwell>", help="perform slot error rate measurement")
# parser.add_argument('--serCont', action="store", nargs='?',const='1', metavar="<dwell>", help="perform continuous slot error rate measurement")
# parser.add_argument('--peak', action="store", nargs='?',const='0.1', metavar="<dwell>", help="peak power measurement, binary search for DAC value")
parser.add_argument('--read', action="store", nargs=1, metavar="<regnum>", help="Reads from the FPGA memory map, given a channel number (0-127)", type=int)
parser.add_argument('--write', action="store", nargs=2, metavar="<regnum>", help="Writes to the FPGA memory map, given a channel number (0-127) and value to be written", type=int)
parser.add_argument('--edfa', action="store", nargs=2, metavar="<edfacmd>", help="Writes either edfa on, edfa off, or flash to the FPGA register controlling the edfa")
parser.add_argument('--send', action="store", nargs=2, metavar="<sendfile>", help="Sends a binary file to the FPGA Modulator along with desired PPM order")
parser.add_argument('--power', action="store", nargs=1, metavar="<power>", help="Turns power on/off on the FPGA board")
parser.add_argument('--dacWrite', action="store", nargs=3, metavar="<dacWrite>", help="Send FSM commands<dac 1=PD, 2=FSM> <channel (0-3)> <value (0-65000)>", type=int)
parser.add_argument('--dacInit', action="store",  nargs=1, metavar="dacInit", help="Initialize DAC PD=1 FSM=2", type=int)
parser.add_argument('--dacUpdate', action="store", nargs=1, metavar="davUpdate", help="Update DAC Values PD=1 FSM=2", type=int)
parser.add_argument('--update', nargs = 1, help="Streams the values in registers 96-117 every 0.1*argument seconds until told to stop")
# parser.add_argument('--interval', action="store", nargs=1, metavar="<interval>", help="Sets the printing interval", type=int)
parser.add_argument('--findCenter', action="store", nargs=1, metavar="<start>", help="Matches the laser wavelength to the center of the FBG", type = int)

parser.add_argument('--testfsm', action="store",  nargs=1, metavar = "<voltage>", help="Takes the maximum voltage the FSM driver can handle to test the throw in all directions", type = int)

argList = parser.parse_args()


handle = fl.FLHandle()
try:
	fl.flInitialise(0)

	vp = argList.v[0]
	#print("Attempting to open connection to FPGALink device {}...".format(vp))
	try:
		handle = fl.flOpen(vp)
	except fl.FLException as ex:
		if ( argList.i ):
			ivp = argList.i[0]
			#print("Loading firmware into {}...".format(ivp))
			fl.flLoadStandardFirmware(ivp, vp);
		#print type(ivp)
		#print type(vp)
			# Long delay for renumeration
			# TODO: fix this hack.  The timeout value specified in flAwaitDevice() below doesn't seem to work
			#time.sleep(3)
			
			#print("Awaiting renumeration...")
			if ( not fl.flAwaitDevice(vp, 30) ):
				raise fl.FLException("FPGALink device did not renumerate properly as {}".format(vp))

			handle = fl.flOpen(vp)
		else:
			raise fl.FLException("Could not open FPGALink device at {} and no initial VID:PID was supplied".format(vp))

	conduit = 1
	if ( argList.c ):
		conduit = int(argList.c[0])

	isNeroCapable = fl.flIsNeroCapable(handle)
	isCommCapable = fl.flIsCommCapable(handle, conduit)
	fl.flSelectConduit(handle, conduit)


	if(argList.send and isCommCapable):
		ppm_order = int(argList.send[1])>>2
		f = open(argList.send[0], 'rb')
		data = [128+ppm_order]
		binary = []
		done = False
		count = 0
		end = 2048
		bin_size = 0xFF
		while not done:
			char = f.read(1)
			if(char == ''):
				done = True
			else:
				data += [ord(char)]
		#print(len(data))
		while(count != len(data)):
			fifo_space = 2048-((0x07&fl.flReadChannel(handle, memMap.get_register('fff'))<<8)+fl.flReadChannel(handle, memMap.get_register('dfp')))
			if(fifo_space>0):
				end+=fifo_space
				if(end>len(data)):
					end = len(data)
				fl.flWriteChannel(handle, memMap.get_register('dat'), bytearray(data[count:end]))
				#print('Data FIFO Pointer = '+str(fl.flReadChannel(handle, memMap.get_register('dfp'))))
				count = end
		ones = 0
		errors = 0
		while(fl.flReadChannel(handle, memMap.get_register('efp')) or fl.flReadChannel(handle, memMap.get_register('fff'))&56):
			errors += fl.flReadChannel(handle, memMap.get_register('err'))
		while(fl.flReadChannel(handle, memMap.get_register('ofp')) or fl.flReadChannel(handle, memMap.get_register('fff'))&196):
			ones += fl.flReadChannel(handle, memMap.get_register('one'))
		#    print('Ones FIFO Pointer = '+str(fl.flReadChannel(handle, memMap.get_register('ofp'))))
		print('errors = '+str(errors))
		print('ones = '+str(ones))

	if(argList.power and isCommCapable):
		reg = 32
		if(argList.power[0] == 'off'):
			cmd = 15
			print('turning power off...')
		elif(argList.power[0] == 'on'):
			cmd = 85
			print('turning power on...')
		else:
			print('not a valid power command')
		for i in range(0, 5):
			fl.flWriteChannel(handle, reg+i, cmd)

        if(argList.testfsm and isCommCapable):

            bias = 80.0
            throw = 50.0
            max_voltage = float(argList.testfsm[0])

            #bias_bits = int(2.4/3.3*bias/max_voltage*65536)
            #throw_bits = int(2.4/3.3*throw/max_voltage*65536)
            bias_bits = 22000
            throw_bits = 12000
            print("Bias: ", bias_bits, "Throw: ", throw_bits)
            fl.flWriteChannel(handle,33, 85)

            time.sleep(2)
            #dac_initialization
            dac.init(handle, 1)
            #for i in range(4):
            #    dac.write_dac(handle, 2,i,bias_bits)    
            #dac.update_dac(handle, 2)

            time.sleep(2)

            while(1):
                

                
                #Towards X+ Channel
                print("Towards X+ Channel")
                dac.write_dac(handle,2,2,bias_bits-throw_bits)
                dac.write_dac(handle, 2,3,bias_bits+throw_bits)
                dac.update_dac(handle, 2)
                time.sleep(2)
                #Towards X- Channel
                print("Toward X- Channel")
                print("Pos Code:", bias_bits+throw_bits, "Neg_Code:", bias_bits-throw_bits)
                dac.write_dac(handle,2,2,bias_bits+throw_bits)
                dac.write_dac(handle,2,3,bias_bits-throw_bits)
                dac.update_dac(handle,2)
                time.sleep(2)
                #Back to Center
                print("Back to Center")
                print("Pos Code:", bias_bits, "Neg_Code:", bias_bits)
                dac.write_dac(handle,2,2,bias_bits)
                dac.write_dac(handle,2,3,bias_bits)
                dac.update_dac(handle,2)
                time.sleep(2)
                #Toward Y+ Channel
                print("Toward Y+ Channel")
                dac.write_dac(handle,2,1,bias_bits-throw_bits)
                dac.write_dac(handle,2,0,bias_bits+throw_bits)
                dac.update_dac(handle,2)
                time.sleep(2) 
                #Toward Y- Channel
                print("Toward Y- Channel")
                dac.write_dac(handle,2,1,bias_bits+throw_bits)
                dac.write_dac(handle,2,0,bias_bits-throw_bits)
                dac.update_dac(handle,2)
                time.sleep(2)
                #Toward Center
                print("Toward Center")
                dac.write_dac(handle,2,1,bias_bits)
                dac.write_dac(handle,2,0,bias_bits)
                dac.update_dac(handle,2)
                time.sleep(2) 
         


	if(argList.edfa and isCommCapable):
		edfa_cmd = ''
		edfa_data = True
		data = []
		count = 0
		last_line = 0
		if(argList.edfa[0] == 'on'):
			edfa_cmd = 'edfa on\r'
		elif(argList.edfa[0] == 'off'):
			edfa_cmd = 'edfa off\r'
		elif(argList.edfa[0] == 'acc'):
			edfa_cmd = 'mode acc\r'
		elif(argList.edfa[0] == 'aopc'):
			edfa_cmd = 'mode aopc\r'
		elif(argList.edfa[0] == 'ldc'):
			edfa_cmd = 'ldc ' + argList.edfa[1] + '\r'
		elif(argList.edfa[0] == 'sldc'):
			edfa_cmd = 'sldc ' + argList.edfa[1] + '\r'
		elif(argList.edfa[0] == 'flash'):
			edfa_cmd = 'flash\r'
		elif(argList.edfa[0] == 'fline'):
			edfa_cmd = 'fline\r'
		elif(argList.edfa[0] == 'esc'):
			edfa_cmd = chr(27)
		elif(argList.edfa[0] == 'aopc'):
			edfa_cmd = 'aopc 5'
		elif(argList.edfa[0] == 'read'):
			edfa_data = True
			data = []
			count = 0
			last_line = 0
			while(edfa_data):
				status = fl.flReadChannel(handle, memMap.get_register('flg'))
				status = status & 0x20
				new_chr = fl.flReadChannel(handle, memMap.get_register('erx'))
				if (status == 0x20):
					data += [new_chr]
					if(data[count] == 13):
						edfa_characters = ''
						for i in range(last_line, count+1):
							edfa_characters += chr(data[i])
						print(edfa_characters)
						last_line = count
					count += 1
		else:
			edfa_cmd = argList.edfa[0]
		edfa_send = False
		edfa.edfa_write_cmd(handle,edfa_cmd)

		if(edfa_cmd == 'fline\r'):
			edfa_data = True
			data = []
			count = 0
			last_line = 0
			valid_return = 0
			while(edfa_data):
				status = fl.flReadChannel(handle, memMap.get_register('flg'))
				status = status & 0x20
				new_chr = fl.flReadChannel(handle, memMap.get_register('erx'))
				if (status == 0x20):
					data += [new_chr]
					if(data[count] == 13):
						edfa_characters = ''
						for i in range(last_line, count+1):
							edfa_characters += chr(data[i])
						for i in range(len(edfa_characters)):
							if(edfa_characters[i] == 'E'):
								print(edfa_characters[i::])
								time.sleep(.1)
								valid_return = 1
						last_line = count
					if(valid_return):
						break
					count += 1

	if( argList.read and isCommCapable ):
		#print("Channel value is")
		print(fl.flReadChannel(handle, argList.read[0]))

	if ( argList.write and isCommCapable ): 
		print(argList.write[1])
		fl.flWriteChannel(handle, argList.write[0], argList.write[1])

	#PD DAC = 1
	#CALIBRATION laser channel 4 on PD DAC
	#FSM DAC = 2
	if (argList.dacInit and isCommCapable ): 
		dac_num = argList.dacInit[0]
		if(dac_num not in [1,2]):
		    print("Not a valid DAC")
		else:
		    dac.init(handle, dac_num)
		    print("Initialized Dac " +str(dac_num))
	
	if (argList.dacWrite and isCommCapable ):
		dac_num = argList.dacWrite[0]
		if((argList.dacWrite[1] > 3 and argList.dacWrite[1] != 7) or argList.dacWrite[2] > 65535 or argList.dacWrite[1] < 0.0):
			print("FSM DAC Address Needs to be between 0 and 3 or 7, and the DAC only takes 0-2.5V as an input cmd")
		else:
			dacVoltage = argList.dacWrite[2]
			dacVoltageWrite = round((3.3*dacVoltage/65536.0),2)
			print("Writing to DAC "+str(dacVoltageWrite)+" V")
			dac.write_dac(handle, dac_num, argList.dacWrite[1], dacVoltage)

	if (argList.dacUpdate and isCommCapable ):
		dac_num = argList.dacUpdate[0]
		#print("updating FSM DAC...")
		dac.update_dac(handle,dac_num)
		print("done")

	if(argList.update and isCommCapable):
		interval = 0.1
		if (argList.update[0] != 0):
			interval = 0.1*int(argList.update[0])
		while(1):
			count = 0
			for reg in range(96, 118):
				num = fl.flReadChannel(handle, reg)
				if not(reg%2):
					value = num<<8
					count += 1
					if(reg == 104):
						count = 1
				else:
					value += num
					if(reg >97 and reg < 110):
						derp = 'Temperature '+str(count)+ ' = '+str(value)
					else:
						derp = 'Current '+str(count)+' = '+str(value)
					print(derp)
			time.sleep(interval)
	
	if(argList.findCenter and isCommCapable):
		init_only = argList.findCenter[0]
		alignment.findCenter(handle,init_only)
		if(init_only):
			fl.flWriteChannel(handle, 13, 131)
			delay = [13,14,15,16,17,18,19,20,21,22,23]
			tec = [160,220]
			for d in range(13,23):
				for t in range(160,225,5):
					fl.flWriteChannel(handle,14,d)
					fl.flWriteChannel(handle,2,t)
					print("Delay: ",d,"TEC: ", t)
					print("FIFO Flags: ", fl.flReadChannel(handle, 57), "Data FIFO: ", fl.flReadChannel(handle,60), "Error FIFO: ", fl.flReadChannel(handle,61), "Ones FIFO: ", fl.flReadChannel(handle,62))
					time.sleep(.5)


	if ( argList.q ):
		if ( isNeroCapable ):
			chain = fl.jtagScanChain(handle, argList.q[0])
			if ( len(chain) > 0 ):
				print("The FPGALink device at {} scanned its JTAG chain, yielding:".format(vp))
				for idCode in chain:
					print("  0x{:08X}".format(idCode))
			else:
				print("The FPGALink device at {} scanned its JTAG chain but did not find any attached devices".format(vp))
		else:
			raise fl.FLException("JTAG chain scan requested but FPGALink device at {} does not support NeroJTAG".format(vp))
	
	if ( argList.p ):
		progConfig = argList.p[0]
		print("Programming device with config {}...".format(progConfig))
		if ( isNeroCapable ):
			fl.flProgram(handle, progConfig)
		else:
			raise fl.FLException("Device program requested but device at {} does not support NeroProg".format(vp))
	
	if ( argList.f and not(isCommCapable) ):
		raise fl.FLException("Data file load requested but device at {} does not support CommFPGA".format(vp))

#     if ( 0 > 1): #isCommCapable and fl.flIsFPGARunning(handle) ):

#         fpga = NodeFPGA(handle)
#         # define channels
#         writechannel = 0x02
#         statuschannel = 0x05
#         resetchannel = 0x08

#         if ( argList.ppm ):
#             M = int(eval(argList.ppm[0]))
#             print "Setting PPM order to",M
#             fpga.setPPM_M(M)
# 	    (writedelay,num_bytes,trackingbyte) = fpga.setModulatorParams(M)
# 	    if not(argList.f):
#                 fpga.setTrackingMode(writechannel,trackingbyte,M)

#         if ( argList.txdel ):
#             delay = int(eval(argList.txdel[0]))
#             print "Setting transmitter loopback delay to %i (0x%X)"%(delay,delay)
#             fpga.setTXdelay(delay)

#         if ( argList.dac ):
#             dacval = int(eval(argList.dac[0]))
#             print "Setting DAC value to %i (0x%X)"%(dacval,dacval)
#             fpga.writeDAC(dacval)

#         if ( argList.prbs ):
# #            dacval = int(eval(argList.dac[0]))
# #            print "Setting DAC value to %i (0x%X)"%(dacval,dacval)
#             print "Enabling PRBS"
#             fpga.usePRBS()
#         else:
#             print "Disabling PRBS"
#             fpga.usePRBS(False)

#         if ( argList.peak ):
#             obslength = float(argList.peak)
#             print
#             print "Measuring peak power..."
#             peakDAC = fpga.binSearchPeak(M,target=1.0/M,obslength=obslength)
#             print "  DAC = %i"%peakDAC
#             print

#         if ( argList.serCont ):
#             #for x in range(5):
#             while True:
# 		    obslength = float(argList.serCont)
# 		    print
# 		    #print "Measuring slot error rate..."
# 		    cycles,errors,ones,ser = fpga.measureSER(obslength=obslength)
# 		    #print " cycles = 0x%-12X"%(cycles)
# 		    #print " errors = 0x%-12X"%(errors)
# 		    #print " ones   = 0x%-12X target=0x%-12X"%(ones,cycles/M)
# 		    print " SER = %e \t ctr-c to quit"%(ser)
# 		    print 
#                     time.sleep(1)

#         if ( argList.ser ):
#             obslength = float(argList.ser)
#             print
#             print "Measuring slot error rate..."
#             cycles,errors,ones,ser = fpga.measureSER(obslength=obslength)
#             print " cycles = 0x%-12X"%(cycles)
#             print " errors = 0x%-12X"%(errors)
#             print " ones   = 0x%-12X target=0x%-12X"%(ones,cycles/M)
#             print " SlotER = %e"%(ser)
#             print

# 	if ( argList.f ):
# 	    dataFile = argList.f[0]
# 	    try:
#                 data_packets = fpga.loadDataFile(dataFile,num_bytes)
# 	    except:
#                 raise NameError('Must input a PPM order or wrong name of file')
# 	    if ( argList.N ):
# 		N = int(argList.N[0])
# 		fpga.writeFileNTimes(writechannel,resetchannel,statuschannel,data_packets,writedelay,vp,N)
#                 fpga.setTrackingMode(writechannel,trackingbyte,M) # quick hack, but should be doing tracking mode after a frame already
# 	    else:
#                 fpga.writeFile(writechannel,resetchannel,statuschannel,data_packets,writedelay,vp)
#                 fpga.setTrackingMode(writechannel,trackingbyte,M) # quick hack, but should be doing tracking mode after a frame already
			
except fl.FLException as ex:
	print(ex)
finally:
	fl.flClose(handle)


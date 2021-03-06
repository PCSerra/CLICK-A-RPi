// Mirrorcle MEMS FSM control class for Raspberry Pi
// Authors: Ondrej Cierny, Peter Grenfell
#include "fsm.h"
#include <unistd.h>
#include <cstdlib>
#include <chrono>
#include <thread>

// Initialize MEMS FSM control board over SPI; filter = cutoff in Hz
//-----------------------------------------------------------------------------
FSM::FSM(std::ofstream &fileStreamIn, zmq::socket_t &pat_health_port_in, zmq::socket_t& fpga_map_request_port_in, zmq::socket_t& fpga_map_answer_port_in, std::vector<zmq::pollitem_t>& poll_fpga_answer_in, uint16_t vBias_dac, uint16_t vMax_dac, float filter) :
fileStream(fileStreamIn), pat_health_port(pat_health_port_in), fpga_map_request_port(fpga_map_request_port_in), fpga_map_answer_port(fpga_map_answer_port_in), poll_fpga_answer(poll_fpga_answer_in)
//-----------------------------------------------------------------------------
{
	// Voltage setting (ref. PicoAmp datasheet)
	voltageBias = vBias_dac;
	voltageMax = vMax_dac;

	// Initialize DAC - AD5664
	oldX = 1; oldY = 1;
	log(pat_health_port, fileStream, "Initializing FSM DAC - Commanding DAC_FULL_RESET = ", DAC_FULL_RESET);
	sendCommand(DAC_FULL_RESET);
	log(pat_health_port, fileStream, "Initializing FSM DAC - Commanding DAC_ENABLE_INTERNAL_REFERENCE = ", DAC_ENABLE_INTERNAL_REFERENCE);
	sendCommand(DAC_ENABLE_INTERNAL_REFERENCE);
	log(pat_health_port, fileStream, "Initializing FSM DAC - Commanding DAC_ENABLE_ALL_DAC_CHANNELS = ", DAC_ENABLE_ALL_DAC_CHANNELS);
	sendCommand(DAC_ENABLE_ALL_DAC_CHANNELS);
	log(pat_health_port, fileStream, "Initializing FSM DAC - Commanding DAC_ENABLE_SOFTWARE_LDAC = ", DAC_ENABLE_SOFTWARE_LDAC);
	sendCommand(DAC_ENABLE_SOFTWARE_LDAC);
	std::this_thread::sleep_for(std::chrono::milliseconds(5)); //initialization delay
	log(pat_health_port, fileStream, "Initializing FSM DAC - Commanding Normalized Angles to (0,0).");
	setNormalizedAngles(0, 0);
}

// Resets angles to (0,0) and turns off LD Bias 
//-----------------------------------------------------------------------------
void FSM::resetFSM()
//-----------------------------------------------------------------------------
{
	setNormalizedAngles(0, 0);
	send_packet_fpga_map_request(fpga_map_request_port, (bool) WRITE, fsm_request_number, (uint16_t) LD_BIAS_CH, (uint8_t) LD_BIAS_OFF);
	fsm_request_number = (fsm_request_number + 1) % 0xFF; //increment request number modulo size(uint8_t)
}

//-----------------------------------------------------------------------------
void FSM::setNormalizedAngles(float x, float y)
//-----------------------------------------------------------------------------
{
	if(abs(x) > 1.0f){
		log(pat_health_port, fileStream,"In fsm.cpp FSM::setNormalizedAngles - Warning! FSM command (x_normalized = ", x, ") exceeds max range (+/- 1). Rounding to limit.");
	}
	if(abs(y) > 1.0f){
		log(pat_health_port, fileStream,"In fsm.cpp FSM::setNormalizedAngles - Warning! FSM command (y_normalized = ", y, ") exceeds max range (+/- 1). Rounding to limit.");
	}
	
	// Clamp to limits
	x = std::max(-1.0f, std::min(x, 1.0f));
	y = std::max(-1.0f, std::min(y, 1.0f));

	int16_t newX = ((int)(voltageMax * x)) & 0xFFFF;
	int16_t newY = ((int)(voltageMax * y)) & 0xFFFF;

	// Write X+, X-, Y+, Y- & Update
	if(newX != oldX || newY != oldY)
	{
		//log(pat_health_port, fileStream,"In fsm.cpp FSM::setNormalizedAngles - Updating FSM position to: ", 
		//"x_normalized = ", x, " -> voltageBias +/- newX = {", voltageBias + newX, ", ", voltageBias - newX,"}. ",
		//"y_normalized = ", y, " -> voltageBias +/- newY = {", voltageBias + newY, ", ", voltageBias - newY,"}. ");
		sendCommand(DAC_CMD_WRITE_INPUT_REG, DAC_ADDR_XP, voltageBias + newX);
		sendCommand(DAC_CMD_WRITE_INPUT_REG, DAC_ADDR_XM, voltageBias - newX);
		sendCommand(DAC_CMD_WRITE_INPUT_REG, DAC_ADDR_YP, voltageBias + newY);
		sendCommand(DAC_CMD_WRITE_INPUT_UPDATE_ALL, DAC_ADDR_YM, voltageBias - newY);
		oldX = newX;
		oldY = newY;
	}
}

//-----------------------------------------------------------------------------
void FSM::forceTransfer()
//-----------------------------------------------------------------------------
{
	sendCommand(DAC_CMD_WRITE_INPUT_REG, DAC_ADDR_XP, voltageBias + oldX);
	sendCommand(DAC_CMD_WRITE_INPUT_REG, DAC_ADDR_XM, voltageBias - oldX);
	sendCommand(DAC_CMD_WRITE_INPUT_REG, DAC_ADDR_YP, voltageBias + oldY);
	sendCommand(DAC_CMD_WRITE_INPUT_UPDATE_ALL, DAC_ADDR_YM, voltageBias - oldY);
}

//-----------------------------------------------------------------------------
void FSM::sendCommand(uint8_t cmd, uint8_t addr, uint16_t value)
//-----------------------------------------------------------------------------
{
  	spiBuffer[0] = cmd | addr; //a, bitwise OR operation
  	spiBuffer[1] = (value & 0xFF00) >> 8; //b, shift value to the right by 8 bits and mask to last 8 bits
  	spiBuffer[2] = value & 0xFF; //c, value to last 8 bits
	fsmWrite(FSM_A_CH, spiBuffer[0]); //write to channel a
	fsmWrite(FSM_B_CH, spiBuffer[1]); //write to channel b
	fsmWrite(FSM_C_CH, spiBuffer[2]); //write to channel c
}

//-----------------------------------------------------------------------------
void FSM::sendCommand(uint32_t cmd)
//-----------------------------------------------------------------------------
{
	spiBuffer[0] = (cmd>>16) & 0xFF; //a, shift cmd to the right by 16 bits and mask to last 8 bits
	spiBuffer[1] = (cmd & 0xFF00) >> 8; //b, shift cmd to the right by 8 bits and mask to last 8 bits
	spiBuffer[2] = cmd & 0xFF; //c, mask to last 8 bits
	fsmWrite(FSM_A_CH, spiBuffer[0]); //write to channel a
	fsmWrite(FSM_B_CH, spiBuffer[1]); //write to channel b
	fsmWrite(FSM_C_CH, spiBuffer[2]); //write to channel c
}

//-----------------------------------------------------------------------------
//write to FSM
void FSM::fsmWrite(uint16_t channel, uint8_t data)
//-----------------------------------------------------------------------------
{
	if(check_fpga_map_value(fpga_map_answer_port, poll_fpga_answer, fpga_map_request_port, (uint16_t) LD_BIAS_CH, (uint8_t) LD_BIAS_ON, fsm_request_number)){
		// LD Bias is ON -> Send FSM command to FPGA:
		//log(pat_health_port, fileStream, "fsmWrite - channel = ", channel, ", data = ", unsigned(data));
		send_packet_fpga_map_request(fpga_map_request_port, WRITE, fsm_request_number, channel, data);
		if(!check_fpga_map_write_request(fpga_map_answer_port, poll_fpga_answer, channel, fsm_request_number)){
			log(pat_health_port, fileStream,"In fsm.cpp FSM::fsmWrite - Warning! FSM write command to channel ", channel, " failed!");
		};
		fsm_request_number = (fsm_request_number + 1) % 0xFF; //increment request number modulo size(uint8_t)

	} else{
		// LD bias is OFF (or the read request failed)
		log(pat_health_port, fileStream, "In fsm.cpp FSM::fsmWrite - LD bias ON check did not pass. Commanding LD bias ON...");
		// Send LD bias ON command to FPGA:
		send_packet_fpga_map_request(fpga_map_request_port, (bool) WRITE, fsm_request_number, (uint16_t) LD_BIAS_CH, (uint8_t) LD_BIAS_ON);

		// Check that message was received and FPGA was written to:
		if(check_fpga_map_write_request(fpga_map_answer_port, poll_fpga_answer, (uint16_t) LD_BIAS_CH, fsm_request_number)){
			// LD Bias is ON -> Send FSM command to FPGA:
			//log(pat_health_port, fileStream, "fsmWrite - channel = ", channel, ", data = ", unsigned(data));
			send_packet_fpga_map_request(fpga_map_request_port, WRITE, fsm_request_number, channel, data);
			if(!check_fpga_map_write_request(fpga_map_answer_port, poll_fpga_answer, channel, fsm_request_number)){
				log(pat_health_port, fileStream,"In fsm.cpp FSM::fsmWrite - Warning! FSM write command to channel ", channel, " failed!");
			};
			fsm_request_number = (fsm_request_number + 1) % 0xFF; //increment request number modulo size(uint8_t)
			
		} else{
			log(pat_health_port, fileStream, "In fsm.cpp FSM::fsmWrite - Warning! LD bias ON write failed!");
		}
	}	
}

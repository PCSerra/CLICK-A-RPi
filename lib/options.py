#!/usr/bin/env python
CHECK_ASSERTS = 1

COMMAND_HANDLERS_COUNT = 1
MESSAGE_TIMEOUT = 5000 # wait 5 seconds for ZeroMQ response

# File management
SYMLINK_MAX = 10

#IPC Port Numbers
TEST_RESPONSE_PORT = "5599"

CH_HEARTBEAT_PORT = "5555"
HK_CONTROL_PORT = "5556"

FPGA_MAP_ANSWER_PORT = "5557"
FPGA_MAP_REQUEST_PORT = "5558"

PAT_HEALTH_PORT = "5559"
PAT_CONTROL_PORT = "5560"
PAT_STATUS_PORT = "5564"

TX_PACKETS_PORT = "5561"
RX_CMD_PACKETS_PORT = "5562"
RX_PAT_PACKETS_PORT = "5563"

#FPGA interface
IPC_USES_SPI = 1
FPGA_SHELL_USES_IPC = 0
FPGA_SHELL_USES_SPI = 1

SPI_FREQ = 1000000
USB_DEVICE_ID = "1d50:602b:0002"

EDFA_READ_WRITE_DELAY = 0.05
EDFA_TIMOUT = 1.0
EDFA_VIRTUAL_REGS_GOOD_FOR = 0.5

#Time at tone packet APID
APID_TIME_AT_TONE = 0x280

#Ground Command IDs
CMD_PL_REBOOT = 0x01
CMD_PL_ENABLE_TIME = 0xC2
CMD_PL_EXEC_FILE = 0x67
CMD_PL_LIST_FILE = 0xFE
CMD_PL_AUTO_DOWNLINK_FILE = 0xAB #Change
CMD_PL_DISASSEMBLE_FILE = 0x15 #Change
CMD_PL_REQUEST_FILE = 0x16 #Change
CMD_PL_UPLINK_FILE = 0xCD
CMD_PL_ASSEMBLE_FILE = 0x39 #Change
CMD_PL_VALIDATE_FILE = 0x40
CMD_PL_MOVE_FILE = 0x41 #Change
CMD_PL_DELETE_FILE = 0x42 #Change
CMD_PL_AUTO_ASSEMBLE_FILE = 0xCC #Change
CMD_PL_SET_PAT_MODE = 0xB3
CMD_PL_SINGLE_CAPTURE = 0xF1
CMD_PL_CALIB_LASER_TEST = 0x4C
CMD_PL_FSM_TEST = 0x28
CMD_PL_RUN_CALIBRATION = 0x32
CMD_PL_TX_ALIGN = 0x87 #Change
CMD_PL_UPDATE_TX_OFFSETS = 0x88 #Change
CMD_PL_UPDATE_FSM_ANGLES = 0x89 #Change
CMD_PL_ENTER_PAT_MAIN = 0x90 #Change
CMD_PL_EXIT_PAT_MAIN = 0x91 #Change
CMD_PL_END_PAT_PROCESS = 0x92 #Change
CMD_PL_SET_FPGA = 0x54
CMD_PL_GET_FPGA = 0x0E
CMD_PL_SET_HK = 0x97
CMD_PL_ECHO = 0x3D
CMD_PL_NOOP = 0x5B
CMD_PL_SELF_TEST = 0x80 #Change
CMD_PL_DWNLINK_MODE = 0xE0 #Do not change - BCT
CMD_PL_DEBUG_MODE = 0xD0 #Do not change - BCT

#Telemetry APIDs
TLM_HK_SYS = 0x312 #TBR
TLM_HK_PAT = 0x313 #TBR
TLM_HK_FPGA_MAP = 0x314 #TBR
TLM_DL_FILE = 0x387 #TBR
TLM_LIST_FILE = 0x3E0
TLM_ASSEMBLE_FILE = 0x3B0 #TBR
TLM_GET_FPGA = 0x3C0
TLM_ECHO = 0x3FF

#Self Test IDs
GENERAL_SELF_TEST = 0x00
LASER_SELF_TEST = 0x01
PAT_SELF_TEST = 0x02

#PAT IPC Command IDs [Shared Command Parameters with c-code (packetdef.h)]
PAT_CMD_PAYLOAD_SIZE = 256 #Only a fixed size is allowed in the C++ code (packetdef.h): add padding if necessary
PAT_CMD_START_PAT = 0x00
PAT_CMD_START_PAT_OPEN_LOOP = 0x01
PAT_CMD_START_PAT_STATIC_POINT = 0x02
PAT_CMD_START_PAT_BUS_FEEDBACK = 0x03
PAT_CMD_START_PAT_OPEN_LOOP_BUS_FEEDBACK = 0x04
PAT_CMD_UPDATE_TX_OFFSET_X = 0x05
PAT_CMD_UPDATE_TX_OFFSET_Y = 0x06
PAT_CMD_END_PAT = 0x07
PAT_CMD_GET_IMAGE = 0x08
PAT_CMD_CALIB_TEST = 0x09
PAT_CMD_CALIB_LASER_TEST = 0x0A
PAT_CMD_FSM_TEST = 0x0B
PAT_CMD_BCN_ALIGN = 0x0C
PAT_CMD_TX_ALIGN = 0x0D
PAT_CMD_UPDATE_FSM_X = 0x0E
PAT_CMD_UPDATE_FSM_Y = 0x0F
PAT_CMD_SELF_TEST = 0x10
PAT_CMD_END_PROCESS = 0x11
#PAT Status Flags
PAT_STATUS_CAMERA_INIT = 0x00
PAT_STATUS_STANDBY = 0x01
PAT_STATUS_MAIN = 0x02
#PAT Main Mode Entry Flag
PAT_TEST_FLAG = 0xFFFF
PAT_FLIGHT_FLAG = 0xAAAA

#Calibration Laser DAC setting
CAL_LASER_DAC_SETTING = 6700

# HK Options Settings
HK_FPGA_REQ_ENABLE = 1
HK_SYS_HK_SEND_ENABLE = 1
HK_FPGA_HK_SEND_ENABLE = 1
HK_PAT_HK_SEND_ENABLE = 1
HK_CH_RESTART_ENABLE = 1
HK_PAT_RESTART_ENABLE = 1
HK_FPGA_RESTART_ENABLE = 1
HK_ALLPKTS_SEND_ENABLE = 1

HK_FPGA_CHECK_PD = 6 #seconds
HK_SYS_CHECK_PD = 5 #seconds
HK_CH_HEARTBEAT_PD = 10 #seconds
HK_PAT_HEALTH_PD = 3 #seconds

# File Handling Options Settings
FL_ERR_EMPTY_DIR = 0x01
FL_ERR_FILE_NAME = 0x02
FL_ERR_SEQ_LEN = 0x03
FL_ERR_MISSING_CHUNK = 0x04
FL_SUCCESS = 0xFF

# Set Time Flag
TIME_SET_ENABLE = 0

FPGA_TELEM_REGS = [range(0,4), range(32,38), range(47,48), range(53,54), [57], range(60,63), range(96,109), range(112,119), range(602,611), range(502,510)]

# For housekeeping/commandhandler interface
CMD_ACK = 0x0F
CMD_ERR = 0xF0

HK_CONTROL_ACK = 0x01
HK_CONTROL_LOG = 0x02

#Error IDs
ERR_HK_RESTART = 0x380 #Change
ERR_FL_FILE_NOT_FOUND = 0x381 #Change
ERR_FL_FILE_INVALID = 0x382 #Change
ERR_DPKT_CRC_INVALID = 0x384 #Change

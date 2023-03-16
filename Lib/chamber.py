import time
import enum

from serialext import _SerialKeywords
from utils import Utils


class RespStatusCode(enum.Enum):
	INVALID_COMMAND_SETTING = 1
	INVALID_REGISTER_SETTING = 2
	DATA_SETTING_ERROR = 4
	INVALID_FORMAT_CONFIGURATION = 8
	CHECKSUM_ERROR = 11
	MONITORING_COMMAND_ERROR = 12
	OTHER_ERRORS = 0


class ModbusRegister(enum.IntEnum):
	TEMP_NPV = 1  # Read current temperature
	TEMP_NSV = 2  # Read seted temperature
	WET_NPV = 3
	WET_NSP = 4
	HUMI_NPV = 5
	HUMI_NSP = 6
	TEMP_MVOUT = 7  # Current temperature percentage control output (MV)
	HUMI_MVOUT = 8  # Current humidity percentage control output (MV)
	C_PID_NO = 9
	NOWSTS = 10     # Displays the run-related status information
	DOCTR_STS = 15
	RUN_TIME_H = 24
	RUN_TIME_M = 25
	RUN_TIME_S = 26
	COM_OPMODE = 101    # Start running PROG/FIX Oper
	FIX_TEMP_TSP = 102  # Temperature Set Point on FIX operation
	FIX_HUMI_TSP = 103  # Humidity Set Point on FIX operation
	OP_MODE = 104       # Set PROG/FIX Operation MODE
	PWR_MODE = 105
	LIGHT_SWITCH = 114  # Turn ON/OFF the light

	NOW_YEAR = 201
	NOW_MONTH = 202
	NOW_DAY = 203
	NOW_AM_PM = 204
	NOW_HOUR = 205
	NOW_MIN = 206

	AL1_OPMODE = 667


class CommandType(enum.Enum):
	RSD = 0
	RRD = 1
	WSD = 2
	WRD = 3
	STD = 4
	CLD = 5


class RunningStatus(enum.Enum):
	OFF = 1
	ON = 2


class Converter(object):
	@staticmethod
	def to_ascii(h):
		list_s = []
		for i in range(0, len(h), 2):
			list_s.append(chr(int(h[i:i + 2], 16)))

		return ''.join(list_s)

	@staticmethod
	def to_hex(s):
		list_h = []
		for c in s:
			list_h.append(str(hex(ord(c))[2:]))

		return ''.join(list_h)

	@staticmethod
	def convert_hex_to_dec(hexTemp):
		temp = int(hexTemp, 16)

		return -(temp & 0x8000) | (temp & 0x7fff)

	@staticmethod
	def convert_dec_to_hex(decTem):
		if decTem >= 0:
			return hex(decTem)[2:].upper().zfill(4)
		else:
			binStr = bin(decTem & 0xFFFF)[2:]
			hexStr = hex(int(binStr, 2))[2:].upper()

			return hexStr


class _TempKeywords(object):
	def __init__(self):
		super().__init__()
		self._ser = _SerialKeywords()

	# region Data Acquisition
	def get_current_temperature(self, register=ModbusRegister.TEMP_NPV):
		resp = self._read_content(register)
		temp = self._calculate_temp(resp)

		return temp

	def get_the_configured_temperature(self, register=ModbusRegister.TEMP_NSV):
		resp = self._read_content(register)
		temp = self._calculate_temp(resp)

		print('The TEMI1000 configured temperature is {:.2f} C'.format(temp))

		return temp

	def _get_running_state(self, register=ModbusRegister.NOWSTS):
		resp = self._read_content(register)

		code = str(resp).split(',')[-1].strip()[:-2]
		state = Utils.to_enum(int(code), RunningStatus)

		return state

	# region Function

	def set_temperature_output(self, temp, register=ModbusRegister.FIX_TEMP_TSP):
		temp = int(temp) * 100
		targetTemp = Converter.convert_dec_to_hex(temp)

		state = self._get_running_state()

		if state is RunningStatus.ON:
			self._start_stop_trigger()

		self._write_content(data=targetTemp, register=register)

	def _start_stop_trigger(self, data='0001', register=ModbusRegister.COM_OPMODE):
		self._write_content(data=data, register=register)

	def deactivate_output(self):
		state = self._get_running_state()

		if state is RunningStatus.ON:
			self._start_stop_trigger()

	def activate_output(self):
		state = self._get_running_state()

		if state is not RunningStatus.ON:
			self._start_stop_trigger()

	def wait_until_temperature_is(self, temp, timeout=3600, interval=5):
		temp = int(temp)
		timeout = int(timeout)
		interval = int(interval)

		timeoutAbs = time.time() + timeout

		while time.time() < timeoutAbs:
			time.sleep(interval)
			currentTemp = self.get_current_temperature()
			if Utils.floatEquals(currentTemp, temp, uncertainty=0.2):
				print('The current temperature reaches the target temperature: {:.2f} C'.format(temp))
				return currentTemp

		raise AssertionError('The temperature not reaches the target temperature after {}'.format(timeout))

	# endregion

	def _check_response(self, response):
		response = str(response)

		if 'OK' in response:
			pass
		elif 'NG' in response:
			errCode = int(response.split('NG')[-1][:2])
			errInfo = Utils.to_enum(errCode, RespStatusCode)
			raise AssertionError('Response failed :{:s}'.format(errInfo.name))
		else:
			raise AssertionError('Command send failed, response :{:s}'.format(response))

	def _splicing_command(self, register, registerCount=1, cmdType=CommandType.RSD, data=None):
		register = Utils.to_enum(register, ModbusRegister).value
		registerCount = int(registerCount)
		cmdType = Utils.to_enum(cmdType, CommandType).name

		sumStr = self._calculate_sum(cmdType, registerCount, register, data)

		if register >= 1000:
			register = str(register)
		else:
			register = str(register).zfill(4)

		# convert to hex
		header = '02'
		address = Converter.to_hex('01')
		cmdType = Converter.to_hex(cmdType)
		registerCount = Converter.to_hex('01')
		register = Converter.to_hex(register)
		comma = Converter.to_hex(',').upper()
		sumStr = Converter.to_hex(sumStr)
		CR = '0D'
		LF = '0A'

		if data is not None:
			data = Converter.to_hex(data)
			command = ''.join([header, address, cmdType, comma, registerCount, comma, register, comma, data, sumStr, CR, LF])
		else:
			command = ''.join([header, address, cmdType, comma, registerCount, comma, register, sumStr, CR, LF])

		return command

	def _calculate_sum(self, cmdType, registerCount, register, data=None):
		"""
		1) Add the ASCII code of characters from the character next to STX one by one up to the character prior to SUM
		2) Represent the lowest one byte of the sum as a hexadecimal notation (2 characters)
		"""
		registerCount = int(registerCount)
		cmdType = Utils.to_enum(cmdType, CommandType).name
		register = Utils.to_enum(register, ModbusRegister).value

		if register >= 1000:
			register = str(register)
		else:
			register = str(register).zfill(4)

		comma = ['2C']
		address = [Converter.to_hex(i) for i in '01']
		registerCount = [Converter.to_hex(i) for i in str(registerCount).zfill(2)]
		register = [Converter.to_hex(i) for i in register]
		cmdType = [Converter.to_hex(i) for i in str(cmdType)]

		if data is not None:
			data = [Converter.to_hex(i) for i in data]

		if data is not None:
			cmdStr = address + cmdType + comma + registerCount + comma + register + comma + data
		else:
			cmdStr = address + cmdType + comma + registerCount + comma + register

		sumStr = ','.join(cmdStr)
		SUM = hex(sum([int(v, 16) for v in sumStr.split(',')]))[-2:]

		return SUM.upper()

	def _calculate_temp(self, response):
		resp = str(response).split(',')
		hexTemp = resp[-1][:4]

		temp = Converter.convert_hex_to_dec(hexTemp) / 100

		return round(temp, 2)

	def _write_content(self, data, register):
		command = self._splicing_command(register, cmdType=CommandType.WSD, data=data)

		self._ser.open_port_connection(self._ser.get_usb_to_serial_port(), baudrate=9600)

		self._ser.write_hex_data('{:s}'.format(command))
		time.sleep(0.1)
		resp = self._ser.read_data()
		self._check_response(resp)

		self._ser.close_all_port_connection()

		return resp

	def _read_content(self, register):
		command = self._splicing_command(register)

		self._ser.open_port_connection(self._ser.get_usb_to_serial_port(), baudrate=9600)

		self._ser.write_hex_data('{:s}'.format(command))
		time.sleep(0.1)
		resp = self._ser.read_data()
		self._check_response(resp)

		self._ser.close_all_port_connection()

		return resp


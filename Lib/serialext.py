import time
import string
import serial
import hashlib

from serial.tools import list_ports
from serial.serialutil import SerialException


class _SerialKeywords(object):
    _clients = {}
    _connections = {}
    _active_connection = None

    @classmethod
    def _check_connectionID(cls, connectionID):
        if connectionID is None:
            connectionID = cls._active_connection

        if connectionID is None:
            raise SerialException('No serial connection established')

        if connectionID not in cls._connections:
            raise SerialException('No serial connection with ID {:s} established'.format(connectionID))

        if cls._connections[connectionID]['clientID'] not in cls._clients:
            raise SerialException('serial connection with ID {:s} exists, but no serial client was found')

        return connectionID

    @classmethod
    def _open_port_connection(cls, port=None, baudrate=921600, timeout=None, **connectParams):
        port = str(port) if port is not None else cls.get_usb_serial_port()
        baudrate = int(baudrate) if baudrate is not None else 926100
        timeout = float(timeout) if timeout is not None else 30

        #print('Start setup port {:s} connection..'.format(port))

        connectParams.update({
            'port': port,
            'baudrate': baudrate,
            'timeout': timeout
        })

        clientID = None

        clientID = hashlib.sha1('{:s}'.format(connectParams.get('port')).encode('utf-8')).hexdigest()
        connectionID = '{:s}-{:d}'.format(clientID, baudrate)

        if clientID not in cls._clients:
            cls._clients[clientID] = {
                'client': serial.Serial(**connectParams),  # type: serial.Serial
                'counter': 0,
            }

        if connectionID not in cls._connections:
            cls._connections[connectionID] = {
                'clientID': clientID,
                'port': port,
                'baudrate': baudrate,
                'timeout': timeout,
            }
            cls._clients[clientID]['counter'] += 1

        cls._active_connection = connectionID

        return connectionID

    @classmethod
    def _get_port_connection_parameters(cls, connectionID=None):
        connectionID = cls._check_connectionID(connectionID)

        return {
            'port': cls._clients[cls._connections[connectionID]['clientID']]['client'].port,
            'baudrate': cls._clients[cls._connections[connectionID]['clientID']]['client'].baudrate,
            'timeout': cls._clients[cls._connections[connectionID]['clientID']]['client'].timeout,
            'bytesize': cls._clients[cls._connections[connectionID]['clientID']]['client'].bytesize,
            'parity': cls._clients[cls._connections[connectionID]['clientID']]['client'].parity,
            'stopbits': cls._clients[cls._connections[connectionID]['clientID']]['client'].stopbits,
            'xonxoff': cls._clients[cls._connections[connectionID]['clientID']]['client'].xonxoff,
            'rtscts': cls._clients[cls._connections[connectionID]['clientID']]['client'].rtscts,
            'dsrdtr': cls._clients[cls._connections[connectionID]['clientID']]['client'].dsrdtr,
            'write_timeout': cls._clients[cls._connections[connectionID]['clientID']]['client'].write_timeout,
            'inter_byte_timeout': cls._clients[cls._connections[connectionID]['clientID']]['client'].inter_byte_timeout,
        }

    @classmethod
    def _close_port_connection(cls, connectionID=None):
        connectionID = cls._check_connectionID(connectionID)

        #print('Closing port {} connection..'.format(cls._clients[cls._connections[connectionID]['clientID']]['client'].port))

        cls._clients[cls._connections[connectionID]['clientID']]['counter'] -= 1

        if cls._clients[cls._connections[connectionID]['clientID']]['counter'] <= 0:
            cls._clients[cls._connections[connectionID]['clientID']]['client'].close()

            del cls._clients[cls._connections[connectionID]['clientID']]['client']
            del cls._clients[cls._connections[connectionID]['clientID']]

        del cls._connections[connectionID]

        cls._active_connection = None if not cls._connections else next(iter(cls._connections.keys()))

        return cls._active_connection

    @classmethod
    def _close_all_port_connection(cls):
        for connectionID in [*cls._connections.keys()]:
            cls._close_port_connection(connectionID)

        cls._active_connection = None

        return cls._active_connection

    @classmethod
    def _switch_port_connection(cls, connectionID):
        if connectionID not in cls._connections:
            raise SerialException('No port connection with ID {:s} established'.format(connectionID))

        cls._active_connection = connectionID

        return connectionID

    @classmethod
    def _write_str_data(cls, data, connectionID=None):
        data = str(data)
        connectionID = cls._check_connectionID(connectionID)

        print('Writing {:s} to serial port'.format(data.strip()))

        try:
            cls._clients[cls._connections[connectionID]['clientID']]['client'].write(data.encode('utf-8'))
            cls._clients[cls._connections[connectionID]['clientID']]['client'].flush()
        except Exception as err:
            raise AssertionError('Write data failed,{}'.format(err))

    @classmethod
    def _write_hexadecimal_data(cls, data, connectionID=None):
        connectionID = cls._check_connectionID(connectionID)

        try:
            cls._clients[cls._connections[connectionID]['clientID']]['client'].write(data)
            cls._clients[cls._connections[connectionID]['clientID']]['client'].flush()
        except Exception as err:
            raise AssertionError('Write data failed,{}'.format(err))

    @classmethod
    def _read_data(cls, connectionID=None):
        connectionID = cls._check_connectionID(connectionID)

        count = cls._clients[cls._connections[connectionID]['clientID']]['client'].inWaiting()
        if count > 0:
            res = cls._clients[cls._connections[connectionID]['clientID']]['client'].read(count)
            cls._clients[cls._connections[connectionID]['clientID']]['client'].flushOutput()
        else:
            print('No data in waiting')

        return res.decode()

    @classmethod
    def _clear_port(cls, connectionID=None):
        connectionID = cls._check_connectionID(connectionID)

        cls._connections[connectionID]['clientID']['client'].flush()

    @staticmethod
    def show_usable_port():
        ports = list_ports.comports()
        portInfo = dict()

        if len(ports) <= 0:
            raise SerialException('Not found any available port!')
        else:
            for p in ports:
                portInfo[p[0]] = p[1]

        return portInfo

    @staticmethod
    def get_usb_serial_port():
        ports = _SerialKeywords.show_usable_port()
        serialPort = None

        for k,v in ports.items():
            if 'USB Serial' in v:
                serialPort = k

        if not serialPort:
            raise SerialException('No USB Serial port in port list')

        return serialPort

    @staticmethod
    def get_usb_relay_port():
        ports = _SerialKeywords.show_usable_port()
        relayPort = None

        for k, v in ports.items():
            if 'USB-SERIAL' in v:
                relayPort = k

        if not relayPort:
            raise SerialException('No USB relay port in port list')

        return relayPort

    @staticmethod
    def get_usb_to_serial_port():
        ports = _SerialKeywords.show_usable_port()
        port = None

        for k, v in ports.items():
            if 'USB-to-Serial' in v:
                port = k

        if not port:
            raise SerialException('No USB-to-Serial port in port list')

        return port

    @staticmethod
    def get_mediatek_ets_port():
        ports = _SerialKeywords.show_usable_port()
        port = None

        for k, v in ports.items():
            if 'ETS' in v:
                port = k

        if not port:
            raise SerialException('No MediaTek ETS port in port list')

        return port

    @staticmethod
    def get_mediatek_usb_vcom_port(timeout=60):
        timeout = int(timeout)
        port = None

        timeoutAbs = time.time() + timeout

        while time.time() < timeoutAbs:
            time.sleep(2)
            ports = _SerialKeywords.show_usable_port()
            for k, v in ports.items():
                if 'USB VCOM' in v:
                    port = k
            if port:
                break

        if not port:
            raise SerialException('No MediaTek USB VCOM port was found in {:d} seconds'.format(timeout))

        return port

    @staticmethod
    def is_usb_vcom_port_exist():
        flag = False
        ports = _SerialKeywords.show_usable_port()

        portInfo = ports.values()

        for info in portInfo:
            if 'VCOM' in info.split(' '):
                flag = True

        return flag

    def open_port_connection(self, port=None, baudrate=921600, timeout=None, **connectParams):
        _SerialKeywords._open_port_connection(port, baudrate, timeout, **connectParams)

    def switch_port_connection(self, connectionID):
        _SerialKeywords._switch_port_connection(connectionID)

    def close_port_connection(self, connectionID=None):
        _SerialKeywords._close_port_connection(connectionID)

    def close_all_port_connection(self):
        _SerialKeywords._close_all_port_connection()

    def write_str_data(self, data, connectionID=None):
        _SerialKeywords._write_str_data(data, connectionID)

    def write_hex_data(self, data, connectionID=None):
        data = str(data).strip()

        if all(s in string.hexdigits for s in data):
            data = bytes.fromhex(data)
        else:
            raise ValueError('Data is not all hexadecimal')

        _SerialKeywords._write_hexadecimal_data(data, connectionID)

    def read_data(self, connectionID=None):
        return _SerialKeywords._read_data(connectionID)

    def send_command(self, command, pause=None):
        command = str(command)
        pause = float(pause) if pause is not None else 0.5

        try:
            self.write_str_data('{:s}\n'.format(command))
            time.sleep(pause)
            resp = self.read_data()
        except Exception as err:
            raise AssertionError('Send command failed, {:s}'.format(command, err))

        return resp








# -*- coding: utf-8 -*-
import numpy as np
import struct
from explorepy.packet import Orientation, Environment, TimeStamp, Disconnect, DeviceInfo, EEG, EEG94, EEG98, EEG99s
from explorepy.filters import Filter

ORN_ID = 13
ENV_ID = 19
TS_ID = 27
DISCONNECT_ID = 111
INFO_ID = 99
EEG94_ID = 144
EEG98_ID = 146
EEG99S_ID = 30
EEG99_ID = 62
EEG94R_ID = 208
EEG98R_ID = 210

PACKET_CLASS_DICT = {
    ORN_ID: Orientation,
    ENV_ID: Environment,
    TS_ID: TimeStamp,
    DISCONNECT_ID: Disconnect,
    INFO_ID: DeviceInfo,
    EEG94_ID: EEG94,
    EEG98_ID: EEG98,
    EEG99S_ID: EEG99s,
    EEG99_ID: EEG99s,
    EEG94R_ID: EEG94_ID,
    EEG98R_ID: EEG98
}


def generate_packet(pid, timestamp, bin_data):
    """Generates the packets according to the pid

    Args:
        pid (int): Packet ID
        timestamp (int): Timestamp
        bin_data: Binary dat

    Returns:
        Packet
    """

    if pid in PACKET_CLASS_DICT:
        packet = PACKET_CLASS_DICT[pid](timestamp, bin_data)
    else:
        print("Unknown Packet ID:" + str(pid))
        print("Length of the binary data:", len(bin_data))
        packet = None
    return packet


class Parser:
    def __init__(self, bp_freq=None, notch_freq=50, socket=None, fid=None, calibre_set=None):
        """Parser class for explore device

        Args:
            socket (BluetoothSocket): Bluetooth Socket (Should be None if fid is provided)
            fid (file object): File object for reading data (Should be None if socket is provided)
            bp_freq (tuple): Tuple of cut-off frequencies of bandpass filter (low cut-off frequency, high cut-off frequency)
            notch_freq (int): Notch filter frequency (50 or 60 Hz)
        """
        self.socket = socket
        self.fid = fid
        self.dt_int16 = np.dtype(np.int16).newbyteorder('<')
        self.dt_uint16 = np.dtype(np.uint16).newbyteorder('<')
        self.time_offset = None
        self.calibre_set = calibre_set
        self.init_set = None
        self.ED_prv = None
        #self.ED_prv = [np.array([0, 0, 1]), np.array([0, 1, 0])]
        if bp_freq is not None:
            assert bp_freq[0] < bp_freq[1], "High cut-off frequency must be larger than low cut-off frequency"
            self.bp_freq = bp_freq
            self.apply_bp_filter = True
        else:
            self.apply_bp_filter = False
            self.bp_freq = (0, 100)  # dummy values
        self.notch_freq = notch_freq

        self.firmware_version = None
        self.filter = None
        if self.apply_bp_filter or notch_freq:
            # Initialize filters
            self.filter = Filter(l_freq=self.bp_freq[0], h_freq=self.bp_freq[1], line_freq=notch_freq)

    def parse_packet(self, mode="print", csv_files=None, outlets=None, dashboard=None):
        """Reads and parses a package from a file or socket

        Args:
            mode (str): logging mode {'print', 'record', 'lsl', 'visualize', None}
            csv_files (tuple): Tuple of csv file objects (EEG_csv_file, ORN_csv_file)
            outlets (tuple): Tuple of lsl StreamOutlet (orientation_outlet, EEG_outlet
            dashboard (Dashboard): Dashboard object for visualization
        Returns:
            packet object
        """
        pid = struct.unpack('B', self.read(1))[0]
        cnt = self.read(1)[0]
        payload = struct.unpack('<H', self.read(2))[0]
        timestamp = struct.unpack('<I', self.read(4))[0]

        # Timestamp conversion
        if self.time_offset is None:
            self.time_offset = timestamp
            timestamp = 0
        else:
            timestamp = (timestamp - self.time_offset) * .0001  # Timestamp unit is .1 ms

        payload_data = self.read(payload - 4)
        packet = generate_packet(pid, timestamp, payload_data)

        if isinstance(packet, DeviceInfo):
            self.firmware_version = packet.firmware_version
        if mode == "print":
            print(packet)

        elif mode == "record":
            assert isinstance(csv_files, tuple), "Invalid csv writer objects!"
            if isinstance(packet, Orientation):
                packet.write_to_csv(csv_files[1])
            elif isinstance(packet, EEG):
                packet.write_to_csv(csv_files[0])

        elif mode == "lsl":
            if isinstance(packet, Orientation):
                packet.push_to_lsl(outlets[0])
            elif isinstance(packet, EEG):
                packet.push_to_lsl(outlets[1])

        elif mode == "visualize":
            if isinstance(packet, EEG):
                if self.notch_freq:
                    packet.apply_notch_filter(exg_filter=self.filter)
                if self.apply_bp_filter:
                    packet.apply_bp_filter(exg_filter=self.filter)
            if isinstance(packet, Orientation):
                self.compute_NED(packet)
            packet.push_to_dashboard(dashboard)

        elif mode == "calibrate":
            #assert isinstance(csv_files, tuple), "Invalid csv writer objects!"
            if isinstance(packet, Orientation):
                packet.write_to_csv(csv_files)

        elif mode == "initialize":
            if isinstance(packet, Orientation):
                th = np.zeros(3)
                T_init = np.zeros((3, 3))
                D = packet.acc / (np.dot(packet.acc, packet.acc) ** 0.5)
                E = np.cross(D, packet.mag)
                E = E / (np.dot(E, E) ** 0.5)

                N = np.cross(E, D)
                N = N / (np.dot(N, N) ** 0.5)
                T_init[0][0] = N[0]
                T_init[0][1] = E[0]
                T_init[0][2] = D[0]

                T_init[1][0] = N[1]
                T_init[1][1] = E[1]
                T_init[1][2] = D[1]

                T_init[2][0] = N[2]
                T_init[2][1] = E[2]
                T_init[2][2] = D[2]

                N_init = np.matmul(np.transpose(T_init), N)
                E_init = np.matmul(np.transpose(T_init), E)
                D_init = np.matmul(np.transpose(T_init), D)
                self.init_set = [T_init, N_init, E_init, D_init]
                self.ED_prv = [E, D]
        return packet

    def read(self, n_bytes):
        """Read n_bytes from socket or file

        Args:
            n_bytes (int): number of bytes to be read

        Returns:
            list of bytes
        """
        if self.socket is not None:
            byte_data = self.socket.recv(n_bytes)
        elif not self.fid.closed:
            byte_data = self.fid.read(n_bytes)
        else:
            raise ValueError("File has been closed unexpectedly!")
        if len(byte_data) != n_bytes:
            raise ValueError("Number of received bytes is less than expected")
            # TODO: Create a specific exception for this case
        return byte_data

    def compute_NED(self, packet):
        #TOCHECK
        [kx, ky, kz, mx_offset, my_offset, mz_offset] = self.calibre_set
        T_init = self.init_set[0]
        N_init = self.init_set[1]
        E_init = self.init_set[2]
        D_init = self.init_set[3]
        D_prv = self.ED_prv[1]
        E_prv = self.ED_prv[0]
        acc = packet.acc
        acc = acc / (np.dot(acc, acc) ** 0.5)
        gyro = packet.gyro * 1.745329e-5 #radian per second
        mag = np.array([0, 0, 0])
        mag[0] = kx * (packet.mag[0] - mx_offset)
        mag[1] = -ky * (packet.mag[1] - my_offset)
        mag[2] = kz * (packet.mag[2] - mz_offset)
        D = acc
        dD = D-D_prv
        da = np.cross(D_prv, dD)
        E = np.cross(D, mag)
        E = E / (np.dot(E, E) ** 0.5)
        dE = E-E_prv
        dm = np.cross(E_prv, dE)
        dg = 0.05 * gyro
        dth = -0.95 * dg + 0.025 * da + 0.025 * dm
        D = D_prv + np.cross(dth, D_prv)
        D = D / (np.dot(D, D) ** 0.5)
        E = E_prv + np.cross(dth, E_prv)
        E = E / (np.dot(E, E) ** 0.5)
        Err = np.dot(D, E)
        D_tmp = D - 0.5*Err*E
        E_tmp = E - 0.5*Err*D
        D = D_tmp / (np.dot(D_tmp, D_tmp) ** 0.5)
        E = E_tmp / (np.dot(E_tmp, E_tmp) ** 0.5)
        D_prv = D
        E_prv = E
        N = np.cross(E, D)
        N = N / (np.dot(N, N) ** 0.5)
        T = np.zeros((3,3))

        T[0][0] = N[0]
        T[0][1] = E[0]
        T[0][2] = D[0]

        T[1][0] = N[1]
        T[1][1] = E[1]
        T[1][2] = D[1]

        T[2][0] = N[2]
        T[2][1] = E[2]
        T[2][2] = D[2]

        T_test = np.matmul(T, T_init.transpose())

        N = np.matmul(T_test.transpose(), N_init)
        E = np.matmul(T_test.transpose(), E_init)
        D = np.matmul(T_test.transpose(), D_init)
        matrix = np.identity(4)
        matrix[0][0] = N[0]
        matrix[0][1] = E[0]
        matrix[0][2] = D[0]

        matrix[1][0] = N[1]
        matrix[1][1] = E[1]
        matrix[1][2] = D[1]

        matrix[2][0] = N[2]
        matrix[2][1] = E[2]
        matrix[2][2] = D[2]
        N = N / (np.dot(N, N) ** 0.5)
        E = E / (np.dot(E, E) ** 0.5)
        D = D / (np.dot(D, D) ** 0.5)
        packet.NED = np.array([N, E, D])
        self.ED_prv = [E, D]
        print(packet.compute_angle())

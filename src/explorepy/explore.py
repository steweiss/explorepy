# -*- coding: utf-8 -*-

from explorepy.bt_client import BtClient
from explorepy.parser import Parser
import bluetooth
import csv
import os
import time
from pylsl import StreamInfo, StreamOutlet
from explorepy.packet import *
import explorepy.filters


class Explore:
    r"""Mentalab Explore device"""
    def __init__(self, n_device=1):
        r"""
        Args:
            n_device (int): Number of devices to be connected
        """
        self.device = []
        self.socket = None
        self.parser = None
        for i in range(n_device):
            self.device.append(BtClient())

    def connect(self, device_name=None, device_addr=None, device_id=0):
        r"""
        Connects to the nearby device. If there are more than one device, the user is asked to choose one of them.

        Args:
            device_name (str): Device name in the format of "Explore_XXXX"
            device_addr (str): The MAC address in format "XX:XX:XX:XX:XX:XX" Either Address or name should be in
            the input

            device_id (int): device id

        """

        self.device[device_id].init_bt(device_name=device_name, device_addr=device_addr)

    def disconnect(self, device_id=None):
        r"""Disconnects from the device

        Args:
            device_id (int): device id (id=None for disconnecting all devices)
        """
        self.device[device_id].socket.close()

    def acquire(self, device_id=0):
        r"""Start getting data from the device

        Args:
            device_id (int): device id (id=None for disconnecting all devices)
        """

        self.socket = self.device[device_id].bt_connect()

        if self.parser is None:
            self.parser = Parser(self.socket)

        is_acquiring = True
        while is_acquiring:
            try:
                packetData = self.parser.parse_packet(mode="print")
            except ValueError:
                # If value error happens, scan again for devices and try to reconnect (see reconnect function)
                print("Disconnected, scanning for last connected device")
                socket = self.device[device_id].bt_connect()
                self.parser.socket = socket
            except bluetooth.BluetoothError as error:
                print("Bluetooth Error: attempting reconnect. Error: ", error)
                self.parser.socket = self.device[device_id].bt_connect()

    def get_blink(self, device_id=0):
        r"""Start getting data from the device
        Print out if script detects looking left/right or blinking

        Blinking is detected if recent value exceeds previous value + threshhold

        Looking left: Looking left causes a value increase in electrode 1 and a decrease in electrode 4
        Check if this case happens to detect looking left

        Looking Right: See looking left, but electrode behaviour is now swapped (4 decreases, 1 increases)

        Args:
            device_id (int): device id (id=None for disconnecting all devices)
        """

        self.socket = self.device[device_id].bt_connect()

        if self.parser is None:
            self.parser = Parser(self.socket)

        is_acquiring = True

        """Initialize compare values"""
        lastVal = 1.0
        lastVal_eyeR_1 = 1.0
        lastVal_eyeR_2 = 1.0

        lastVal_eyeL_1 = -1.0
        lastVal_eyeL_2 = 1.0

        eyeState_L_1 = 1.0
        eyeState_R_1 =1.0

        filter = []

        direction = None

        for i in range(4):
            filter.append(explorepy.filters.Filter())

        while is_acquiring:
            try:
                """Apply filter for better detection"""
                packetData = self.parser.parse_packet(filter=filter)
                if isinstance(packetData, EEG):
                    for i in range(len(packetData.data[0])):
                        compValue = packetData.data[1, i]
                        compValue_eyeR_1 = packetData.data[0, i]
                        compValue_eyeL_1 = packetData.data[3, i]

                        if lastVal + 0.00035 < compValue < lastVal + 0.0007:

                        """Check for looking Right or left"""
                        if lastVal_eyeL_1 - 0.00005 > compValue_eyeL_1  and compValue_eyeR_1 >\
                            lastVal_eyeR_1 + 0.00005:
                            print("looking right")

                        elif lastVal_eyeR_1 - 0.00005 > compValue_eyeR_1  and compValue_eyeL_1 >\
                            lastVal_eyeL_1 + 0.00005:
                            print("looking Left")

                        lastVal = compValue
                        lastVal_eyeR_1 = compValue_eyeR_1
                        lastVal_eyeL_1 = compValue_eyeL_1

            except ValueError:
                # If value error happens, scan again for devices and try to reconnect (see reconnect function)
                print("Disconnected, scanning for last connected device")
                socket = self.device[device_id].bt_connect()
                self.parser.socket = socket
            except bluetooth.BluetoothError as error:
                print("Bluetooth Error: attempting reconnect. Error: ", error)
                self.parser.socket = self.device[device_id].bt_connect()

    def record_data(self, file_name, do_overwrite=False, device_id=0):
        r"""Records the data in real-time

        Args:
            file_name (str): output file name
            device_id (int): device id
            do_overwrite (bool): Overwrite if files exist already
        """
        time_offset = None
        exg_out_file = file_name + "_ExG.csv"
        orn_out_file = file_name + "_ORN.csv"

        assert not (os.path.isfile(exg_out_file) and do_overwrite), exg_out_file + " already exists!"
        assert not (os.path.isfile(orn_out_file) and do_overwrite), orn_out_file + " already exists!"

        self.socket = self.device[device_id].bt_connect()

        if self.parser is None:
            self.parser = Parser(self.socket)

        filter = []
        for i in range(4):
            filter.append(explorepy.filters.Filter())

        with open(exg_out_file, "w") as f_eeg, open(orn_out_file, "w") as f_orn:
            f_orn.write("TimeStamp, ax, ay, az, gx, gy, gz, mx, my, mz \n")
            f_orn.write(
                "hh:mm:ss, mg/LSB, mg/LSB, mg/LSB, mdps/LSB, mdps/LSB, mdps/LSB, mgauss/LSB, mgauss/LSB, mgauss/LSB\n")
            f_eeg.write("TimeStamp, ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8\n")
            csv_eeg = csv.writer(f_eeg, delimiter=",")
            csv_orn = csv.writer(f_orn, delimiter=",")

            is_acquiring = True
            print("Recording...")

            while is_acquiring:
                try:
                    packet = self.parser.parse_packet(mode="record", csv_files=(csv_eeg, csv_orn), filter=filter)
                    if time_offset is not None:
                        packet.timestamp = packet.timestamp-time_offset
                    else:
                        time_offset = packet.timestamp

                except ValueError:
                    # If value error happens, scan again for devices and try to reconnect (see reconnect function)
                    print("Disconnected, scanning for last connected device")
                    self.parser.socket = self.device[device_id].bt_connect()
                except bluetooth.BluetoothError as error:
                    print("Bluetooth Error: Probably timeout, attempting reconnect. Error: ", error)
                    self.parser.socket = self.device[device_id].bt_connect()

    def push2lsl(self, n_chan, device_id=0, mode=None):
        r"""Push samples to two lsl streams

        Args:
            device_id (int): device id
            n_chan (int): Number of channels (4 or 8)
            mode (str): Filter Settings (Either Lowpass for ECG or Bandpass for EEG )
        """

        self.socket = self.device[device_id].bt_connect()

        if self.parser is None:
            self.parser = Parser(self.socket)

        if mode is not None:
            assert(mode=="ECG" or mode =="EEG"), "Please enter either ECG or EEG"
        assert (n_chan is not None), "Number of channels missing"
        assert (n_chan == 4) or (n_chan == 8), "Number of channels should be either 4 or 8"

        info_orn = StreamInfo('Mentalab', 'Orientation', 9, 20, 'float32', 'explore_orn')
        info_eeg = StreamInfo('Mentalab', 'EEG', n_chan, 250, 'float32', 'explore_eeg')

        orn_outlet = StreamOutlet(info_orn)
        eeg_outlet = StreamOutlet(info_eeg)

        is_acquiring = True

        while is_acquiring:
            print("Pushing to lsl...")

            try:
                self.parser.parse_packet(mode="lsl", outlets=(orn_outlet, eeg_outlet), filter=mode)
            except ValueError:
                # If value error happens, scan again for devices and try to reconnect (see reconnect function)
                print("Disconnected, scanning for last connected device")
                self.socket = self.device[device_id].bt_connect()
                time.sleep(1)
                self.parser = Parser(self.socket)

            except bluetooth.BluetoothError as error:
                print("Bluetooth Error: Probably timeout, attempting reconnect. Error: ", error)
                self.socket = self.device[device_id].bt_connect()
                time.sleep(1)
                self.parser = Parser(self.socket)

    def visualize(self):
        r"""Start visualization of the data in the viewer (NOT IMPLEMENTED)

        Returns:

        """
        pass


if __name__ == '__main__':
    pass

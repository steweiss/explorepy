# -*- coding: utf-8 -*-

from explorepy.bt_client import BtClient
from explorepy.parser import Parser
from explorepy.dashboard.dashboard import Dashboard
import bluetooth
import csv
import os
import time
from pylsl import StreamInfo, StreamOutlet
from threading import Thread, Timer
import numpy as np


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
        self.m_dashboard = None
        for i in range(n_device):
            self.device.append(BtClient())

    def connect(self, device_name=None, device_addr=None, device_id=0):
        r"""
        Connects to the nearby device. If there are more than one device, the user is asked to choose one of them.

        Args:
            device_name (str): Device name in the format of "Explore_XXXX"
            device_addr (str): The MAC address in format "XX:XX:XX:XX:XX:XX" Either Address or name should be in the input
            device_id (int): device id (not needed in the current version)

        """

        self.device[device_id].init_bt(device_name=device_name, device_addr=device_addr)

    def disconnect(self, device_id=None):
        r"""Disconnects from the device

        Args:
            device_id (int): device id (not needed in the current version)
        """
        self.device[device_id].socket.close()

    def acquire(self, device_id=0, duration=None):
        r"""Start getting data from the device

        Args:
            device_id (int): device id (not needed in the current version)
            duration (float): duration of acquiring data (if None it streams data endlessly)
        """

        self.socket = self.device[device_id].bt_connect()

        if self.parser is None:
            self.parser = Parser(socket=self.socket)

        is_acquiring = [True]

        def stop_acquiring(flag):
            flag[0] = False

        if duration is not None:
            Timer(duration, stop_acquiring, [is_acquiring]).start()
            print("Start acquisition for ", duration, " seconds...")

        while is_acquiring[0]:
            try:
                self.parser.parse_packet(mode="print")
            except ValueError:
                # If value error happens, scan again for devices and try to reconnect (see reconnect function)
                print("Disconnected, scanning for last connected device")
                socket = self.device[device_id].bt_connect()
                self.parser.socket = socket
            except bluetooth.BluetoothError as error:
                print("Bluetooth Error: attempting reconnect. Error: ", error)
                self.parser.socket = self.device[device_id].bt_connect()

        print("Data acquisition stopped after ", duration, " seconds.")

    def record_data(self, file_name, do_overwrite=False, device_id=0, duration=None):
        r"""Records the data in real-time

        Args:
            file_name (str): output file name
            device_id (int): device id (not needed in the current version)
            do_overwrite (bool): Overwrite if files exist already
            duration (float): Duration of recording in seconds (if None records endlessly).
        """
        # Check invalid characters
        if set(r'[<>/{}[\]~`]*%').intersection(file_name):
            raise ValueError("Invalid character in file name")

        time_offset = None
        exg_out_file = file_name + "_ExG.csv"
        orn_out_file = file_name + "_ORN.csv"

        assert not (os.path.isfile(exg_out_file) and do_overwrite), exg_out_file + " already exists!"
        assert not (os.path.isfile(orn_out_file) and do_overwrite), orn_out_file + " already exists!"

        self.socket = self.device[device_id].bt_connect()

        if self.parser is None:
            self.parser = Parser(socket=self.socket)

        with open(exg_out_file, "w") as f_exg, open(orn_out_file, "w") as f_orn:
            f_orn.write("TimeStamp, ax, ay, az, gx, gy, gz, mx, my, mz \n")
            f_orn.write(
                "hh:mm:ss, mg/LSB, mg/LSB, mg/LSB, mdps/LSB, mdps/LSB, mdps/LSB, mgauss/LSB, mgauss/LSB, mgauss/LSB\n")
            f_exg.write("TimeStamp, ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8\n")
            csv_exg = csv.writer(f_exg, delimiter=",")
            csv_orn = csv.writer(f_orn, delimiter=",")

            is_acquiring = [True]

            def stop_acquiring(flag):
                flag[0] = False

            if duration is not None:
                Timer(duration, stop_acquiring, [is_acquiring]).start()
                print("Start recording for ", duration, " seconds...")
            else:
                print("Recording...")

            while is_acquiring[0]:
                try:
                    self.parser.parse_packet()
                    packet = self.parser.parse_packet(mode="record", csv_files=(csv_exg, csv_orn))
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
            print("Recording finished after ", duration, " seconds.")

    def push2lsl(self, n_chan, device_id=0, duration=None):
        r"""Push samples to two lsl streams

        Args:
            device_id (int): device id (not needed in the current version)
            n_chan (int): Number of channels (4 or 8)
            duration (float): duration of data acquiring (if None it streams endlessly).
        """

        self.socket = self.device[device_id].bt_connect()

        if self.parser is None:
            self.parser = Parser(socket=self.socket)

        assert (n_chan is not None), "Number of channels missing"
        assert n_chan in [2, 4, 8], "Number of channels should be either 2, 4 or 8"

        info_orn = StreamInfo('Mentalab', 'Orientation', 9, 20, 'float32', 'explore_orn')
        info_exg = StreamInfo('Mentalab', 'ExG', n_chan, 250, 'float32', 'explore_exg')

        orn_outlet = StreamOutlet(info_orn)
        exg_outlet = StreamOutlet(info_exg)

        is_acquiring = [True]

        def stop_acquiring(flag):
            flag[0] = False

        if duration is not None:
            Timer(duration, stop_acquiring, [is_acquiring]).start()
            print("Start pushing to lsl for ", duration, " seconds...")
        else:
            print("Pushing to lsl...")

        while is_acquiring[0]:

            try:
                self.parser.parse_packet(mode="lsl", outlets=(orn_outlet, exg_outlet))
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
        print("Data acquisition finished after ", duration, " seconds.")

    def visualize(self, n_chan, device_id=0, bp_freq=(1, 30), notch_freq=50, calibre_file=None):
        r"""Visualization of the signal in the dashboard

        Args:
            n_chan (int): Number of channels device_id (int): Device ID (in case of multiple device connection)
            device_id (int): Device ID (not needed in the current version)
            bp_freq (tuple): Bandpass filter cut-off frequencies (low_cutoff_freq, high_cutoff_freq), No bandpass filter
            if it is None.
            notch_freq (int): Line frequency for notch filter (50 or 60 Hz), No notch filter if it is None
        """
        self.socket = self.device[device_id].bt_connect()
        with open(calibre_file, "r") as f_calibre:
            csv_reader_calibre = csv.reader(f_calibre, delimiter=",")
            calibre_set = list(csv_reader_calibre)
            calibre_set = np.asarray(calibre_set[1], dtype=np.float64)

        if self.parser is None:
            self.parser = Parser(socket=self.socket, bp_freq=bp_freq, notch_freq=notch_freq, calibre_set=calibre_set)

        self.m_dashboard = Dashboard(n_chan=n_chan)
        self.m_dashboard.start_server()

        thread = Thread(target=self._io_loop)
        thread.setDaemon(True)
        thread.start()
        self.m_dashboard.start_loop()

    def _io_loop(self, device_id=0):
        is_acquiring = True
        is_initialized = False

        # Wait until dashboard is initialized.
        while not hasattr(self.m_dashboard, 'doc'):
            print('wait')
            time.sleep(.2)
        while is_acquiring:
            if is_initialized:
                try:
                    packet = self.parser.parse_packet(mode="visualize", dashboard=self.m_dashboard)
                except ValueError:
                    # If value error happens, scan again for devices and try to reconnect (see reconnect function)
                    print("Disconnected, scanning for last connected device")
                    socket = self.device[device_id].bt_connect()
                    self.parser.socket = socket
                except bluetooth.BluetoothError as error:
                    print("Bluetooth Error: attempting reconnect. Error: ", error)
                    self.parser.socket = self.device[device_id].bt_connect()
            else:
                try:
                    packet = self.parser.parse_packet(mode="initialize")
                    if hasattr(packet, 'NED'):
                        if self.parser.init_set is not None:
                            is_initialized = True

                except ValueError:
                    # If value error happens, scan again for devices and try to reconnect (see reconnect function)
                    print("Disconnected, scanning for last connected device")
                    socket = self.device[device_id].bt_connect()
                    self.parser.socket = socket
                except bluetooth.BluetoothError as error:
                    print("Bluetooth Error: attempting reconnect. Error: ", error)
                    self.parser.socket = self.device[device_id].bt_connect()

    def calibrate(self, device_id=0, file_name=None, do_overwrite=False, duration=None):
        r"""Start getting data from the device

        Args:
            device_id (int): device id (id=None for disconnecting all devices)
        """
        if set(r'[<>/{}[\]~`]*%').intersection(file_name):
            raise ValueError("Invalid character in file name")

        time_offset = None
        calibre_set_file = file_name + "_calibre_set.csv"
        calibre_out_file = file_name + "_calibre_coef.csv"

        assert not (os.path.isfile(calibre_set_file) and do_overwrite), calibre_set_file + " already exists!"
        assert not (os.path.isfile(calibre_out_file) and do_overwrite), calibre_out_file + " already exists!"

        self.socket = self.device[device_id].bt_connect()

        if self.parser is None:
            self.parser = Parser(socket=self.socket)

        with open(calibre_set_file, "w") as f_set:
            f_set.write("TimeStamp, ax, ay, az, gx, gy, gz, mx, my, mz \n")
            csv_set = csv.writer(f_set, delimiter=",")
            isCalibrating = [True]

            def stop_acquiring(flag):
                flag[0] = False

            if duration is not None:
                Timer(duration, stop_acquiring, [isCalibrating]).start()
                print("Collecting the calibration set for ", duration, " seconds...")
            else:
                Timer(100, stop_acquiring, [isCalibrating]).start()
                print("Collecting the calibration set for 100 seconds...")
            while isCalibrating[0]:
                try:
                    self.parser.parse_packet()
                    packet = self.parser.parse_packet(mode="calibrate", csv_files=csv_set)
                except ValueError:
                    # If value error happens, scan again for devices and try to reconnect (see reconnect function)
                    print("Disconnected, scanning for last connected device")
                    socket = self.device[device_id].bt_connect()
                    self.parser.socket = socket
                except bluetooth.BluetoothError as error:
                    print("Bluetooth Error: attempting reconnect. Error: ", error)
                    self.parser.socket = self.device[device_id].bt_connect()

            if duration is not None:
                print("Data acquisition finished after ", duration, " seconds.")
            else:
                print("Data acquisition finished after 100 seconds.")
            f_set.close()
        with open(calibre_set_file, "r") as f_set, open(calibre_out_file, "w") as f_coef:
            f_coef.write("kx, ky, kz, mx_offset, my_offset, mz_offset\n")
            csv_reader = csv.reader(f_set, delimiter=",")
            csv_coef = csv.writer(f_coef, delimiter=",")
            #for row in csv_reader:
            #    print(row)
            np_set = list(csv_reader)
            np_set = np.array(np_set[1:], dtype=np.float)
            #print(np_set)
            #print(len(np_set))
            mag_set_x = np.sort(np_set[:, -3])
            mag_set_y = np.sort(np_set[:, -2])
            mag_set_z = np.sort(np_set[:, -1])
            mx_offset = 0.5 * (mag_set_x[0] + mag_set_x[-1])
            my_offset = 0.5 * (mag_set_y[0] + mag_set_y[-1])
            mz_offset = 0.5 * (mag_set_z[0] + mag_set_z[-1])
            kx = 0.5 * (mag_set_x[-1] - mag_set_x[0])
            ky = 0.5 * (mag_set_y[-1] - mag_set_y[0])
            kz = 0.5 * (mag_set_z[-1] - mag_set_z[0])
            k = np.sort(np.array([kx,ky,kz]))
            kx = k[1] / kx
            ky = k[1] / ky
            kz = k[1] / kz
            calibre_set = np.array([kx, ky, kz, mx_offset, my_offset, mz_offset])
            csv_coef.writerow(calibre_set)
            f_set.close()
            f_coef.close()




if __name__ == '__main__':
    pass

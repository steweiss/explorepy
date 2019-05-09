import numpy
import scipy
from scipy.signal import butter, lfilter
from scipy import zeros, signal, random


class Filter:
    def __init__(self):
        self.cutoffA = 0.5
        self.cutoffB = 20
        self.sample_frequency = 250.0
        self.order = 5
        self.cutOffLow = 80
        self.b = signal.firwin(5, [self.cutoffA/(0.5*self.sample_frequency), self.cutoffB/(0.5*self.sample_frequency)])
        self.z = signal.lfilter_zi(self.b, 1)


    def set_bandpass(self, a, b, fs, order):
        self.cutoffA = a
        self.cutoffB = b
        self.sample_frequency = fs
        self.order = order

    def butter_bandpass(self):
        nyq = 0.5*self.sample_frequency
        low_a = self.cutoffA/nyq
        high_b = self.cutoffB/nyq
        b, a = butter(self.order, [low_a, high_b], btype='band')
        return b, a

    def apply_band(self, data):
        data_filt = data
        for i, x in enumerate(data):
            data_filt, self.z = signal.lfilter(self.b, 1, [x], zi=self.z)
        return data_filt

    def set_lowpass(self, a, fs, order):
        self.cutOffLow = a
        self.sample_frequency = fs
        self.order = order

    def butter_lowpass(self):
        nyq = 0.5 * self.sample_frequency
        low = self.cutoffA / nyq
        b, a = butter(self.order, low, btype='low')
        return b, a

    def apply_lowpass(self, data):
        b, a = self.butter_lowpass()
        filt_data = lfilter(b, a, data)
        return filt_data

    def is_not_used(self):
        pass

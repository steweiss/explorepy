import explorepy
import numpy as np
import os
import csv
from tkinter.filedialog import askopenfilename
from tkinter import Tk
import mne
import matplotlib.pyplot as plt


def load_eeg_marker(filename, dir):
    eeg = np.zeros((0, 5))
    markers = []
    with open(os.path.join(dir, filename) + "_eeg.csv") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                # Header
                line_count += 1
            else:
                if row:
                    eeg_row = np.array(row, dtype="float")[np.newaxis, :]
                    eeg = np.concatenate((eeg, eeg_row), axis=0)
                line_count += 1

    with open(os.path.join(dir, filename) + "_marker.csv", "r") as marker_file:
        csv_reader = csv.reader(marker_file, delimiter=',')
        for row in csv_reader:
            if row:
                val = np.array(row, dtype="float")[0]
                markers.append(val)
    return eeg, np.array(markers)


def extract_epoch(eeg, markers):
    epoch = None
    idx_start = np.argmax(eeg[:, 0] > markers[0])
    idx_end = np.argmax(eeg[:, 0] > markers[1])
    epoch = eeg[idx_start:idx_end, 1:]
    return epoch


def array2mne(epoch):
    sfreq = 250.  # Sampling frequency
    # times = np.arange(0, epoch.shape[0]/sfreq, 1./sfreq)  # Use 10000 samples (10s)
    epoch = epoch.T
    ch_types = 'eeg'
    ch_names = ['O1', 'C3', 'C4', 'Fp1']
    montage = mne.channels.read_montage(kind="standard_1020", ch_names=ch_names)
    info = mne.create_info(ch_names=montage.ch_names, sfreq=sfreq, ch_types=ch_types, montage=montage)
    raw = mne.io.RawArray(epoch, info)
    return raw


def extract_bandpower(eeg, normalize=True):
    bandpower = np.zeros((4, 4))
    psds, freqs = mne.time_frequency.psd_welch(eeg, fmin=1, fmax=45)
    band_lim = [(1, 4), (4, 8), (8, 12), (12, 30)]

    for i, limits in enumerate(band_lim):
        idx = np.logical_and(freqs >= limits[0], freqs < limits[1])
        bandpower[i, :] = psds[:, idx].sum(axis=1)
    if normalize:
        bandpower /= psds.sum(axis=1)
    return bandpower


root = Tk()
filename_before = askopenfilename(title="Select file recorded before experience")

explorepy.tools.bin2csv(filename_before, do_overwrite=True)

filename_exp = askopenfilename(title="Select file recorded during experience")
explorepy.tools.bin2csv(filename_exp, do_overwrite=True)
root.destroy()

head_path, full_filename = os.path.split(filename_before)
name_before, _ = os.path.splitext(full_filename)
EEG_before, markers_before = load_eeg_marker(name_before, head_path)

head_path, full_filename = os.path.split(filename_exp)
name_exp, _ = os.path.splitext(full_filename)
EEG_exp, markers_exp = load_eeg_marker(name_exp, head_path)

epoch_before = extract_epoch(EEG_before, markers_before)
epoch_exp = extract_epoch(EEG_exp, markers_exp)

before_mne = array2mne(epoch_before)
exp_mne = array2mne(epoch_exp)

before_mne.notch_filter(50)
before_mne.filter(l_freq=.5, h_freq=40)
exp_mne.notch_filter(50)
exp_mne.filter(l_freq=.5, h_freq=40)

scalings = {'eeg': .0002}
before_mne.plot(n_channels=4, scalings=scalings, title='EEG plot (before)', show=True, block=True)
exp_mne.plot(n_channels=4, scalings=scalings, title='EEG plot (Tank experience)', show=True, block=True)

bp_before = extract_bandpower(before_mne)
bp_exp = extract_bandpower(exp_mne)

fig, axes = plt.subplots(2)
before_mne.plot_psd(fmin=1, fmax=40, n_fft=256, ax=axes[0], show=False)
exp_mne.plot_psd(fmin=1, fmax=40, n_fft=256, ax=axes[1], show=False)
axes[0].set_ylim([-5, 25])
axes[0].set_title('Power Spectral Density (before)')
axes[1].set_ylim([-5, 25])
axes[1].set_title('Power Spectral Density (experiment)')
# plt.tight_layout()
plt.show()

# Plot camparison of band powers
ind = np.arange(bp_before.shape[0])
width = 0.3
fig, axes = plt.subplots(2, 2)
ch_names = ['O1', 'C3', 'C4', 'Fp1']
for ax, pow_bef, pow_exp, ch_name in zip(axes.flatten(), bp_before.T, bp_exp.T, ch_names):
    rects1 = ax.bar(ind - width/2, pow_bef, width, label='Before experiment')
    rects2 = ax.bar(ind + width/2, pow_exp, width, label='During experiment')

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel('Relative power')
    ax.set_title(ch_name)
    ax.set_xticks(ind)
    ax.set_xticklabels(('Delta', 'Theta', 'Alpha', 'Beta'))
    ax.legend()
plt.tight_layout()
plt.show()

print("Done!")

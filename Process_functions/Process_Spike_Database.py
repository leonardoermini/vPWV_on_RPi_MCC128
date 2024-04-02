# This script is intended to be used on a .txt file created using the Spike2
# script "G:\My Drive\UniTo\vPWV\Spike2 config\Scripts\TriggeredTextExport_LE.s2s". 
# The .txt file is a database of Doppler-shift epochs of T sec in which a PW is recorded. 
# The present script is intended to test the "vPWV_TD_percentage" function on all epochs
# in order to inspect the computed velocity profiles and footprints.

import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import PTTcomputation

# Parameters
flag_process = True
flag_fft = True
Nepochs2plot = 16

# Import epochs from file
fs = 6250 # [Hz]
T = 0.5   # [sec]
Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
filename = askopenfilename() # show an "Open" dialog box and return the path to the selected file
data = np.loadtxt(filename, comments=('"',' '), delimiter=",", usecols=1, unpack=False)

# Unpack epochs
X = int(T*fs)
Nepochs = int( len(data) / (X+1))
epochs = np.zeros((X+1, Nepochs))
for i in range(Nepochs):
    epochs[ :, i ] = data[ i*(X+1) : (i+1)*(X+1) ]
epochs = epochs[ :-1, : ] # remove the last sample to match fs
time = np.arange(0, T, 1/fs)
print('Number of epochs loaded = %d' % (Nepochs))

# Compute average power spectrum
if flag_fft:
    for i in range(Nepochs):
        Sxx = np.fft.rfft( epochs[ :, i ] )
        if i > 0:
            Sxx_avg += Sxx
        else:
            Sxx_avg = Sxx
    Sxx_avg = Sxx_avg /( Nepochs)
    Pxx_avg = 20 * np.log10( np.abs(Sxx_avg) + 1e-12 )
    freq = np.fft.rfftfreq(time.shape[-1], d=1/fs)
    Pxx_tot = sum(Pxx_avg) / len(freq)
    Pxx_1k = sum(Pxx_avg[100:1000]) / 1000
    fig = plt.figure()
    title = 'Average power spectrum (%d epochs). Average power: %ddB (0.1-5kHz), %ddb (0.1-1kHz)' % (Nepochs, Pxx_tot, Pxx_1k)
    plt.title(title)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Power (dB)')
    plt.plot(freq, Pxx_avg)
    plt.show()

# Process Nepochs2plot epochs at time and plot the results
if flag_process:
    
    division = int( Nepochs / Nepochs2plot)
    remainder = Nepochs % Nepochs2plot
    indexes = np.zeros(division + 1, dtype=int)
    indexes[:division] = Nepochs2plot
    indexes[-1] = remainder

    for k in range(division+1):

        if False:
            # Plot the epochs superimposed
            fig = plt.figure()
            title = 'Doppler-shift epochs'
            plt.title(title)
            plt.xlabel('Samples')
            plt.ylabel('Voltage (V)')
            [plt.plot(time, epochs[:, i]) for i in range(Nepochs)]

        # Compute the envelope
        profile = np.zeros((X, Nepochs2plot))
        latency = np.zeros(Nepochs2plot)
        footprint = np.zeros(Nepochs2plot, dtype=int)
        for i in range(indexes[k]):
            latency[i], profile[:, i] = PTTcomputation.vPWV_TD_percentage( epochs[:, i + k*Nepochs2plot], fs )
            if latency[i] == latency[i]:
                footprint[i] = int(latency[i] * fs)

        # Plot the computed profiles superimposed to the doppler-shift
        cols = 4
        rows = int(np.ceil(indexes[k] / cols))
        if rows < 2:
            cols = 2
            rows = int(np.ceil(indexes[k] / cols))
        fig, axs = plt.subplots(ncols=cols, nrows=rows)
        title = 'Doppler-shift epochs profiled'
        plt.suptitle(title)
        count = 0
        for i in range(rows):
            for j in range(cols):
                if count == Nepochs2plot:
                    axs[i][j].axis('off')
                else:
                    axs[i][j].plot(time, epochs[:, i + j + k*Nepochs2plot])
                    axs[i][j].plot(time, profile[:, i+j])
                    if latency[i] == latency[i]:
                        axs[i][j].plot(latency[i+j], profile[footprint[i+j], i+j], marker="o", markersize=2, markeredgecolor="red", markerfacecolor="red")
                    count += 1
        plt.show()
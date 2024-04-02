# This script is intended to be used for analyzing Doppler epochs by means of
# PTTcomputation routine and comparing the results from Spike2 epochs with those
# from RPi epochs. The present script reads Doppler epochs from: 1) a .txt file
# created using the Spike2 script 
# "G:\My Drive\UniTo\vPWV\Spike2_files\Scripts\TriggeredTextExport_LE.s2s" 
# and 2) a .csv file created by RPi.
# After importing all epochs the script focuses only on a specific subset of
# problematic epochs (previously identified) in order to understand the reasons
# of the different results

import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askopenfilename
from tabulate import tabulate
import PTTcomputation

def compute_and_plot(e, focus, nametitle):
    # Initialize
    Nf = len(focus)
    ef = e[focus , :]
    profile = np.zeros((Nf, X))
    latency = np.zeros(Nf)
    footprint = np.zeros(Nf, dtype=int)
    # Compute
    for i in range(Nf):
        latency[i], profile[i, :] = PTTcomputation.vPWV_TD_percentage( ef[i, :], FS )
        if latency[i] == latency[i]:
            footprint[i] = int(latency[i] * FS)
    # Plot
    cols = int( np.ceil( np.sqrt(Nf) ) )
    rows = cols
    time = np.arange(0, T, 1/FS)
    fig, axs = plt.subplots(ncols=cols, nrows=rows)
    title = 'Doppler-shift epochs profiled: ' + nametitle
    plt.suptitle(title)
    count = 0
    for i in range(rows):
        for j in range(cols):
            k = i + j
            if count == Nf:
                axs[i][j].axis('off')
            else:
                axs[i][j].plot(time, ef[k, :])
                axs[i][j].plot(time, profile[k, :])
                axs[i][j].set_title(str( np.round( (D/100) / latency[k], 2) ))
                if latency[k] == latency[k]:
                    axs[i][j].plot(latency[k], profile[k, footprint[k]], \
                                   marker="o", markersize=2, markeredgecolor="red", markerfacecolor="red")
                count += 1

    return latency, profile, footprint

# ------------------------------------------------------------------------------------------------

# Parameters
D = 34              # [cm]
FS = 6250           # [Hz]
T = 0.5             # [sec]
X = int(T*FS)

# ------------------------------------------- RPi ------------------------------------------------

# Import epochs from file
Tk().withdraw()
filename = askopenfilename(filetypes=[("csv files", "csv")])
e_rpi = np.loadtxt(filename, comments=('"',' '), delimiter=",", skiprows=5, unpack=False)
nonanepochs = ~np.isnan( e_rpi[ :, -2 ] )
e_rpi = e_rpi[ nonanepochs, :-2 ] # remove epochs that led to nan values and also the last two samples of each epochs
Ne_rpi = int( e_rpi.shape[0] )
print('RPi epochs loaded = %d' % (Ne_rpi))

# ------------------------------------------- Spike2 ---------------------------------------------

# Import epochs from file
Tk().withdraw()
filename = askopenfilename(filetypes=[("text files", "txt")])
data = np.loadtxt(filename, comments=('"',' '), delimiter=",", usecols=1, unpack=False)
# Unpack epochs
Ne_spike = int( len(data) / (X+1))
e_spike = np.zeros((Ne_spike, X+1 ))
for i in range(Ne_spike):
    e_spike[ i, : ] = data[ i*(X+1) : (i+1)*(X+1) ]
e_spike = e_spike[ nonanepochs, :-1 ] # remove epochs that led to nan values and the last sample of each epochs
Ne_spike = int(e_spike.shape[0])
print('Spike2 epochs loaded = %d' % (Ne_spike))

# --------------------------------------- Comparison ----------------------------------------------
e_focus = [26,42,47,48,49,55,56,58,61,65,70] # problematic epochs

[ latency_spike, profile_spike, footprint_spike ] = compute_and_plot(e_spike, e_focus, 'Spike2')
[ latency_rpi, profile_rpi, footprint_rpi ] = compute_and_plot(e_rpi, e_focus, 'RPi')
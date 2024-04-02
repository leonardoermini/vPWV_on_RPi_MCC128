# The present script is intended to re-process the doppler epochs acquired by
# RPi by using PTTcomputation.py The scripts reads the Doppler epochs from the
# .csv file created by RPi, process them using PTTcomputation.py and finally,
# write the new results in a new .csv file that is a copy of the original file
# but contains the new vPWV values and is named with the current date and time.

import csv
import datetime
import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import PTTcomputation

# Parameters
FS = 6250           # [Hz]
T = 0.5             # [sec]
X = int(T*FS)       # [samples]

# Load cuff-probe distance and Doppler epochs from .csv file
Tk().withdraw()
src_filename = askopenfilename(filetypes=[("csv files", "csv")])
D = np.loadtxt(src_filename, comments=('"',' '), delimiter=",", skiprows=1, usecols=0, unpack=False)[0]
e = np.loadtxt(src_filename, comments=('"',' '), delimiter=",", skiprows=5, unpack=False)
nonanepochs = ~np.isnan( e[ :, -2 ] )
e = e[ nonanepochs, :-2 ] # remove epochs that led to nan values and also the last two samples of each epochs
Ne = int( e.shape[0] )
print('RPi epochs loaded = %d' % (Ne))

# Re-Process Doppler epochs
profile = np.zeros((Ne, X))
latency = np.zeros(Ne)
vpwv = np.zeros(Ne)
footprint = np.zeros(Ne, dtype=int)
for i in range(Ne):
    latency[i], profile[i, :] = PTTcomputation.vPWV_TD_percentage( e[i, :], FS )
    if latency[i] == latency[i]:
        footprint[i] = int(latency[i] * FS)
        vpwv[i] = (D/100) / latency[i]

# Plot
cols = int( np.ceil( np.sqrt(Ne) ) )
rows = cols
time = np.arange(0, T, 1/FS)
fig, axs = plt.subplots(ncols=cols, nrows=rows)
title = 'RPi Doppler epochs processed'
plt.suptitle(title)
count = 0
for i in range(rows):
    for j in range(cols):
        k = i + j
        if count == Ne:
            axs[i][j].axis('off')
        else:
            axs[i][j].plot(time, e[k, :])
            axs[i][j].plot(time, profile[k, :])
            axs[i][j].set_title(str( np.round( (D/100) / latency[k], 2) ))
            if latency[k] == latency[k]:
                axs[i][j].plot(latency[k], profile[k, footprint[k]], \
                                marker="o", markersize=2, markeredgecolor="red", markerfacecolor="red")
            count += 1

# Read the original .csv file
with open(src_filename, "r", newline="") as f:
    reader = csv.reader(f)
    rows = list(reader)
# Update the vpwv values
rows[4] = vpwv
# Write the original .csv content to a new .csv file 
now = datetime.datetime.now()
dst_filename = src_filename[:-4] + '_reprocessed_' + now.strftime("%Y_%m_%d_%H-%M-%S") + '.csv'
with open(dst_filename, "x", newline="") as f:
    writer = csv.writer(f)
    # Write each row
    for row in rows:
        writer.writerow(row)
print('Data saved')
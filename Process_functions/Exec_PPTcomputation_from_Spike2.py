import os
import numpy as np
import PTTcomputation

# Import epoch from temp.txt file
filename = 'tempIN.txt'
filepath = os.path.join("C:\\Users\\Public\\Documents", filename)
epoch = np.loadtxt(filepath, delimiter=",", unpack=False)
fs = int(epoch[-1])
epoch = epoch[:-1]

# Process Doppler epoch
latency, profile = PTTcomputation.vPWV_TD_percentage( epoch, fs )

# Write the results to a txt file
filename = 'tempOUT.txt'
filepath = os.path.join("C:\\Users\\Public\\Documents", filename)
resultfile = open(filepath, "w")
resultfile.write( str(latency) )
resultfile.close()
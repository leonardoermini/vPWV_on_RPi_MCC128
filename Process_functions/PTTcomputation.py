# This module is used to perform the computation of the Pulse Transit Time (PTT)
# throught the main function vPWV_TD _percentage: it process a Doppler epoch of
# length T sec and returns the time at which the Pulse Wave (PW) footprint is
# located, i.e., the ptt from the beginning of the Dopler epoch.

# The following modules are imported when either any of the functions in the
# module, or the whole module, are imported
import numpy as np
import math
import statsmodels.api as sm
from scipy.signal import find_peaks

def window_rms(x, window_size):
    # Compute the Root Mean Square value of a signal (x) using a mobile window of a specified length (window_size)
    x2 = [i ** 2 for i in x]                                # it is a list comprehension: x2 is equal to x.^2
    window = np.ones(int(window_size)) / float(window_size) # rescale the window weigths w.r.t. the window length
    rms = (np.sqrt(np.convolve(x2, window,'same')))         # the mode 'same' returns a vector of the same length of x with boundary effects visible
    return rms

def time_domain_profiler( x, fs):
    # x: doppler-shift vector of length T sec [Volts]
    # fs: sampling frequency [Hz]
    dx = np.diff(x)                             # first derivative of doppler-shift
    dx = electrical_spike_removal( dx )         # remove elctrical spikes (single sample)
    profile = window_rms( dx, fs/100);          # first derivative envelope
    profile = np.append(profile, profile[-1])   # padding to match len(x), duplicating the last sample
    return profile

def electrical_spike_removal( dx ):
    # dx = doppler first derivative
    SPIKE_TH = 0.3                          # [Volts]
    idx = np.where(np.abs(dx) > SPIKE_TH)   # check forthe presence of abnormal electrical spikes in the first derivative (i.e., dx)
    if len(idx) > 0:                        # replace the spikes in dx with nearby values (i.e., the average between i+2 and i-1)
        for i in idx:                       # note: a single sample in x affects two contiguos samples in dx (i and i+1)
            dx[i] = (dx[i+2] + dx[i-1]) / 2
            dx[i+1] = (dx[i+2] + dx[i-1]) / 2
    return dx                               # returns the doppler first derivative without the electrical spikes

def vPWV_TD_percentage( x, fs ):
    # This function computes the time-domain envelope of the Doppler-shift signal
    # and identifies the PW footprint as the 5% of the peak prominence
    # x: doppler-shift signal vector of length T sec [Volts]
    # fs: sampling frequency [Hz]
    # ptt: footprint ptt [sec]
    # profile: time-domain profile/envelope [n.u.]
    
    # Parameters
    T = len(x) * fs         # Doppler length [sec]
    SPAN = 0.1              # percentage of signal length to be used with the smoothing function
    BS = 0.1 * fs           # baseline window [sec] at the beginning of the signal in which I assume no PW is present
    MPW = 0.05 * fs         # minimum peak width [sec]
    TH = 5                  # threshold as percentage of peak prominence
    P_1K_TH = 0             # threshold value estimated by PW_database_inflating_pressure [dB]

    # The Doppler average power in the frequency band 0.1-1kHz is used to check
    # if it is plausible that signal effectively recorded the passage of a PW
    Sxx = np.fft.rfft( x )                      # compute the real Spectrum by Discrete Fourier Transfor (DFT)
    Pxx = 20 * np.log10( np.abs(Sxx) + 1e-12 )  # compute the Power Spectral Density (PSD) [dB]
    Pxx_avg = sum( Pxx[100:1000] ) / 1000       # average the PSD in the 0.1-1 kHz frequency band [dB]

    if Pxx_avg > P_1K_TH:

        # Envelope computation
        profile = time_domain_profiler( x, fs)

        # Envelope Smoothing
        points = np.arange(0, len(profile), 1)                                                # support vector used for smoothing
        smooth = sm.nonparametric.lowess( profile, points, frac=SPAN, it=0, is_sorted=True )  # lowess non-paramteric smoothing
        profile = smooth[:, 1]
        
        # Envelope Normalization
        profile = profile - np.min(profile)
        profile = profile / np.max(profile)

        # Envelope Peak identification, starting from BS
        [peaks, property] = find_peaks( profile[int(BS):], width=math.floor(MPW) )

        # Footprint identification
        if len(peaks) > 0:
            # Peak position
            peak = int(peaks[0] + BS)
            
            # Identify the local minimum within Peak and BS/2
            valley =  np.argmin( profile[ int(BS/2) : peak ] ) 
            valley = int(BS/2) + valley

            # Threshold is set at 5% of the peak prominence
            H = (profile[peak] - profile[valley]) / 100 * TH + profile[valley]  # compute the peak prominence as the height of the peak from the valley
            percentage = np.argmin( abs(profile[valley:peak] - H) ) # identify the threshold crossing starting from the valley
            percentage = valley + percentage                  # identify the threshold crossing starting from the beginning of the signal

            # Convert the PTT from samples in seconds
            ptt = percentage / fs
        else:
            ptt = float('NaN')
            profile = float('NaN')
    else:
        ptt = float('NaN')
        profile = float('NaN')

    # Return the Pulse Transit Time and the Doppler time-domain profile
    return ptt, profile

def plot_timeseries(title, t, x):
    fig, ax = plt.subplots()
    ax.plot(t, x)
    ax.set_title(title)
    ax.set_xlabel('Time (sec)')
    ax.set_ylabel('Amplitude (Volts)')
    fig.show()
    return ax

def plot_spectrogram(title, x, fs):
    NFFT = 256
    ff, tt, Sxx = stft(x, window='hann', fs=fs, nperseg=NFFT, noverlap=int(NFFT/2),
                boundary=None, scaling='psd')
    Sxx = 20 * np.log10( np.abs(Sxx) + 1e-12 )
    fig, ax = plt.subplots()
    ax.pcolormesh(tt, ff, Sxx, cmap='viridis', shading='gouraud')
    ax.set_title(title)
    ax.set_xlabel('Time (sec)')
    ax.set_ylabel('Frequency (Hz)')
    fig.show()
    return ax

def _test():
    T = 0.5                                                                 # [sec]
    FS = 5000                                                               # [Hz]
    tc = np.linspace(0, T/4, int(T/4*FS), endpoint=False)                   # time vector support for chirp
    c1 = chirp(tc, f0=100, f1=3000, t1=T/4, method='hyperbolic')            # first half of the PW
    c2 = chirp(tc, f0=3000, f1=100, t1=T/4, method='hyperbolic')            # second half of the PW
    w = 1 + gaussian(T*FS, std=int(T*FS/7))                                 # gaussian window used for amplitude modulation
    n = 0.5 * np.random.randn(int(T/4*FS))                                  # white noise
    x = w * np.concatenate((n, n+c1, n+c2, n))                              # doppler epoch synthesis
    x = x / np.max(x)                                                       # normalize synthetic doppler epoch
    t = np.linspace(0, T, int(T*FS), endpoint=False)                        # time vector support for doppler
    ax_t = plot_timeseries("Synthetic Doppler: time-domain", t, x)          # plot doppler in time domain
    ax_f = plot_spectrogram("Synthetic Doppler: frequency-domain", x, FS)   # plot doppler in frequency domain
    ptt, profile = vPWV_TD_percentage( x, FS )                              # identify the pulse wave footprint
    ax_t.plot(t, profile)                                                   # plot profile over the time domain plot
    ax_f.plot(t, profile*FS/2, color='black')                               # plot profile over the frequency domain plot
    ptt_idx = int(ptt*FS)                                                   # extract the index corresponding to ppt
    ax_t.plot(ptt, profile[ptt_idx], color='red', 
              marker='*', markersize='14')                                  # plot footprint over the time domain plot
    ax_f.plot(ptt, profile[ptt_idx]*FS/2, color='red', 
              marker='*', markersize='14')                                  # plot footprint over the frequency domain plot
    

# The following lines are executed only when the module is invocked as a script.
# They are used to test the PTTcomputation module: i) generating a synthetic
# Doppler epoch containing a PW and ii) analyzing it by vPWV_TD_percentage in
# order to identify its footprint
if __name__ == "__main__":
    from scipy.signal import chirp, stft
    from scipy.signal.windows import gaussian
    import matplotlib.pyplot as plt
    _test()
from __future__ import print_function
import sys, os
import time
import datetime
import csv
import uuid
import numpy as np
from collections import deque
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog
from pyqtgraph.Qt.QtCore import QTimer
from pyqtgraph.Qt.QtGui import QSurfaceFormat
from GUI_DialogDeltaX import Ui_Dialog
from GUI_DialogTh import Ui_DialogThreshold
from GUI_MainWindow import Ui_MainWindow
from Process_functions import PTTcomputation

flag_synthetic = True

if not flag_synthetic:
    # Import the libraries
    import RPi.GPIO as GPIO # type: ignore
    from daqhats import mcc128, OptionFlags, HatIDs, AnalogInputMode, AnalogInputRange # type: ignore
    from daqhats_utils import select_hat_device, chan_list_to_mask
    # Initialize GPIO pins
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(24, GPIO.OUT)

# General Parameters
SIGNALS_FS = 500                        # [Hz]
DOPPLER_FS = 6250                       # [Hz]
T_DOPPLER = 0.5                         # [sec]
T_SIGNALS = 10                          # [sec]
UPDATE_INTERVAL = 50                    # [msec]
X_SIGNALS = int(T_SIGNALS*SIGNALS_FS)   # [samples]
X_DOPPLER = int(T_DOPPLER*DOPPLER_FS)   # [samples]
Y_SIGNALS = [-1, 1]                     # [Volts]
ECG_TH = 1.0                            # [Volts]
P_TH = 4                                # [mmHg]
P_FACTOR = -1000                        # [mmHg/Volts]
breath_window = 0.5                     # [sec]
breath_th_percentage = 0.4              # [n.u.]
breath_th_update_time = 1.0             # [sec]
breath_exp_time = 2.0                   # [sec]
cuff_inflation_time = 50                # [msec] @20psi
cuff_deflation_time = 10                # [sec]
channels_signals = [0, 4]
channels_doppler = [1, 5]
patient_id = uuid.uuid4()

########################################### MAIN CLASSES ##################################################

class DeltaXDialog(QDialog, Ui_Dialog):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.PatientIDLineEdit.setText(str(patient_id))
    def accept(self):
        Win.dx = float(self.deltaxSpinBox.text())
        super().accept()
    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        sys.exit()

class ThresholdDialog(QDialog, Ui_DialogThreshold):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.ecgSpinBox.setValue(Win.ecg_th)
        self.inflationSpinBox.setValue(Win.inflation_time)
        self.delaySpinBox.setValue(int(Win.delay_vpwv*1000))

class MainWindow(QMainWindow, Ui_MainWindow):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle(str(patient_id))
        # Set vPWV plot here because it will remain the same
        self.plot3.setUp('vPWV', 'y')
        # set buttons
        self.signalsBtn.toggled.connect(self.toggle_play)
        self.vpwvBtn.toggled.connect(self.start_measure_vpwv)
        self.userMarkersBtn.clicked.connect(self.record_user_markers)
        self.triggerBtn.clicked.connect(self.vpwv_measurement)
        self.settingsBtn.clicked.connect(self.open_settings)
        self.fullscreenBtn.clicked.connect(self.toggle_fullscreen)
        self.dopplerBtn.toggled.connect(self.toggle_tv)
        # set timer breath & ecg
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.frame = 0
        # set timer doppler & pressure
        self.timer_tv = QTimer()
        self.timer_tv.timeout.connect(self.update_tv)
        # Initialize attributes
        self.elapsed = deque(maxlen=1000)
        self.flag_exp = False
        self.flag_ecg = False
        self.flag_vpwv = False
        self.flag_nodeflation = True
        self.delay_vpwv = float(0)
        self.ecg_th = float(ECG_TH)
        self.breath_th = float(0)
        self.inflation_time = cuff_inflation_time
        self.deflation_start = float(0)
        self.breath_th_timer = float(0)
        self.breath_exp_timer = float(0)
        # Initialize variables to save results
        now = datetime.datetime.now()
        self.filename = now.strftime("%Y_%m_%d_%H-%M-%S") + '_vPWV_Data.csv'
        self.doppler = np.zeros(X_DOPPLER+2)
    
    def toggle_play(self):
        if self.signalsBtn.isChecked():
            # set plots
            self.plot1.clear(), self.plot2.clear()
            self.plot1.setUp('Breath', 'Volts', 'g', X_SIGNALS, SIGNALS_FS)
            self.plot2.setUp('ECG', 'Volts', 'g', X_SIGNALS, SIGNALS_FS)
            # start the scan
            self.initialize_MCC_scan('Signals')
            self.start_MCC_scan()
            self.t_start = time.perf_counter()
            self.fpsLastUpdate = time.perf_counter()
            self.timer.start(UPDATE_INTERVAL)
        else:
            self.timer.stop()
            self.stop_MCC_scan()

    def toggle_tv(self):
        if self.dopplerBtn.isChecked():
            # set plots
            self.plot1.clear(), self.plot2.clear()
            self.plot1.setUp('Pressure', 'mmHg', 'g', X_SIGNALS*(DOPPLER_FS//SIGNALS_FS), DOPPLER_FS)
            self.plot2.setUpSonogram('Doppler', 'g', X_SIGNALS*(DOPPLER_FS//SIGNALS_FS), DOPPLER_FS)
            # start the scan
            self.initialize_MCC_scan('DopplerTV')
            self.start_MCC_scan()
            self.t_start = time.perf_counter()
            self.fpsLastUpdate = time.perf_counter()
            self.timer_tv.start(UPDATE_INTERVAL)
        else:
            # stop the scan
            self.timer_tv.stop()
            self.stop_MCC_scan()

############################### INITIALIZE, START AND STOP ACQUISITION #######################################
    
    def initialize_MCC_scan(self, label):
        if flag_synthetic:
            print('Synthetic scan initialized: ' + label)
        else:
            if label=='Signals':
                self.input_mode = AnalogInputMode.SE
                self.input_range = AnalogInputRange.BIP_2V
                self.scan_rate = SIGNALS_FS
                self.samples_per_channel = 0
                self.options = OptionFlags.CONTINUOUS
            elif label=='Doppler':
                self.input_mode = AnalogInputMode.SE
                self.input_range = AnalogInputRange.BIP_2V
                self.scan_rate = DOPPLER_FS
                self.samples_per_channel = X_DOPPLER
                self.options = OptionFlags.DEFAULT
            elif label=='DopplerTV':
                self.input_mode = AnalogInputMode.SE
                self.input_range = AnalogInputRange.BIP_2V
                self.scan_rate = DOPPLER_FS
                self.samples_per_channel = 0
                self.options = OptionFlags.CONTINUOUS
            self.address = select_hat_device(HatIDs.MCC_128)
            self.hat = mcc128(self.address)
            self.hat.a_in_mode_write(self.input_mode)
            self.hat.a_in_range_write(self.input_range)
            if label=='Signals':
                self.channel_mask = chan_list_to_mask(channels_signals)
            elif label=='Doppler' or label=='DopplerTV':
                self.channel_mask = chan_list_to_mask(channels_doppler)
            print('Scan initialized: ' + label)
            

    def start_MCC_scan(self):
        if not flag_synthetic:
            self.hat.a_in_scan_start(self.channel_mask, self.samples_per_channel, self.scan_rate, self.options)
        print('Scan started...')

    def stop_MCC_scan(self):
        if not flag_synthetic:
            self.hat.a_in_scan_stop()
            self.hat.a_in_scan_cleanup()
        print('Scan stopped')
    
    def check_MCC_errors(self, read_result):
        if read_result.hardware_overrun:
            print('\n\nHardware overrun: exiting...\n')
            clean_up(), sys.exit()
        elif read_result.buffer_overrun:
            print('\n\nBuffer overrun: exiting...\n')
            clean_up(), sys.exit()
        elif read_result.timeout:
            print('\n\nTimeout: exiting...\n')
            clean_up(), sys.exit()

########################################### MAIN LOOP ##################################################
    
    def update(self):
        # Read new data
        if flag_synthetic == False:
            breath_new, ecg_new = self.read(-1)
        else:
            breath_new = self.read_synthetic(0.5, -2, 0.2, SIGNALS_FS)
            ecg_new = self.read_synthetic(1, 0, 2, SIGNALS_FS)
        self.frame += 1
        nn = len(breath_new)
        # Update the arrays and plot the curves
        self.plot1.curveUpdate(breath_new)
        self.plot2.curveUpdate(ecg_new)

        # Check if cuff deflation is still in progress
        now = time.perf_counter()
        if not self.flag_nodeflation and (now - self.deflation_start > cuff_deflation_time):
            self.flag_nodeflation = True
        # Check if breath threshold has to be updated
        if now - self.breath_th_timer > breath_th_update_time:
            self.breath_th = self.th_estimate(self.plot1.data, breath_th_percentage)
            self.breath_th_timer = now

        if self.flag_vpwv and self.flag_exp and self.flag_nodeflation:
            # ECG threshold crossing and scatter plot
            ecgMarkers_new, self.flag_ecg = self.ecg_th_crossing(ecg_new, self.ecg_th)
            self.plot2.markersUpdate(ecgMarkers_new)
            # Breath scatter plot without th crossing
            breathDataM_new = np.zeros(len(breath_new), dtype=bool)
            self.plot1.markersUpdate(breathDataM_new)
            if self.flag_ecg:
                self.vpwv_measurement()
        else:
            self.flag_exp = False
            breathDataM_new = np.zeros(nn, dtype=bool)
            if now - self.breath_exp_timer > breath_exp_time:
                # Search threshold cross in the past breath_window sec
                st = -int(breath_window*SIGNALS_FS)
                self.flag_exp = self.breath_th_crossing( self.plot1.data[ st : ], self.breath_th )
                if self.flag_exp:
                    self.breath_exp_timer = now
                    breathDataM_new[-1] = True
            # Breath threshold crossing scatter plot
            self.plot1.markersUpdate(breathDataM_new)
            # ECG threshold crossing and scatter plot
            ecgMarkers_new, self.flag_ecg = self.ecg_th_crossing(ecg_new, self.ecg_th)
            self.plot2.markersUpdate(ecgMarkers_new)
        self.measure_fps()

    def update_tv(self):
        # Read new data
        if flag_synthetic == False:
            doppler_new, pressure_new = self.read(-1)
            pressure_new = pressure_new * P_FACTOR
        else:
            pressure_new = self.read_synthetic(1, 0, 0.2, DOPPLER_FS)
            doppler_new = self.read_synthetic(1, 1, 1500, DOPPLER_FS)
        self.frame += 1
        # Update the array and plot the pressure curve
        self.plot1.curveUpdate(pressure_new)
        # Update the array, compute stft and plot the sonogram
        self.plot2.sonogramUpdate(doppler_new)
        self.measure_fps()

    def measure_fps(self):
        # measure fps
        self.t_end = time.perf_counter()
        self.elapsed.append(self.t_end - self.t_start)
        self.t_start = self.t_end
        # update fps at most once every 0.2 secs
        if self.t_end - self.fpsLastUpdate > 0.2:
            self.fpsLastUpdate = self.t_end
            average = np.mean(self.elapsed)
            fps = 1/average
            self.TitleLabel.setText('FPS: %0.2f - Breath: %0.3f - ECG: %0.2f - Delay: %dms - Inflation: %dms' \
                                     % (fps, self.breath_th, self.ecg_th, self.delay_vpwv*1000, self.inflation_time))

#################################### READ NEW ACQUIRED DATA #######################################
    
    def read(self, samples):
        # this function read the new data from adc (all available=-1) 
        read_result = self.hat.a_in_scan_read_numpy(samples, 5.0)
        self.check_MCC_errors(read_result)
        ch1 = read_result.data[::2]
        ch2 = read_result.data[1::2]
        return ch1, ch2
    
    def read_synthetic(self, amp, offset, f, fs):
        # Define the frequency and amplitude of the sine wave
        t_min = self.frame * (UPDATE_INTERVAL/1000) # s
        t_max = (self.frame + 1) * (UPDATE_INTERVAL/1000) # s
        t = np.arange(t_min, t_max, 1/fs) # s
        y = offset + amp * np.sin(2 * np.pi * f * t) + amp/5 * np.random.randn(len(t))
        return y

    @staticmethod
    def read_synthetic_Tsec(fs):
        t = np.arange(0, 1, 1/fs) # s
        y = 0.5 * np.sin(2 * np.pi * 1000 * t)
        return y

################################## REAL-TIME DATA MANIPULATION #####################################
    @staticmethod
    def breath_th_crossing(data, th):
        flag = False
        n = len(data)
        # compute the linear fit
        if n > 0 and not np.any(np.isnan(data)):
            x = np.arange(0, n, 1)
            p = np.polyfit(x, data, 1)
            data = p[0] * x + p[1]
        # create a mask of samples above and below threshold
        mask = np.array(data > th, dtype=int)
        # crossing is find as nonzero elements in the first derivative of the mask
        diff_mask = np.diff(mask) < 0
        idx = np.nonzero(diff_mask)
        # if th crossing is detected, update the flag
        if idx[0].size > 0:
            flag = True
        return flag
    
    @staticmethod
    def ecg_th_crossing(data, th):
        flag = False
        n = len(data)
        # create a mask of samples above and below threshold
        mask = np.array(data > th, dtype=int)
        # crossing is find in the first derivative of the mask
        diff_mask = np.diff(mask) > 0
        idx = np.nonzero(diff_mask) 
        markers = np.zeros(n, dtype=bool)
        if idx[0].size > 0:
            markers[idx] = True
            flag = True
        return markers, flag
    
    @staticmethod
    def th_estimate(y, factor):
        max = np.max(y)
        min = np.min(y)
        th = min + ( (max - min) * factor )
        return th
    
    def open_settings(self):
        self.DialTh = ThresholdDialog()
        self.DialTh.uploadBtn.clicked.connect(self.modify_settings)
        self.DialTh.show()

    def modify_settings(self):
        self.ecg_th = float(self.DialTh.ecgSpinBox.text())
        self.inflation_time = int(self.DialTh.inflationSpinBox.text())
        self.delay_vpwv = float(self.DialTh.delaySpinBox.text())/1000


#################################### MANAGE VPWV MEASUREMENT #######################################

    def start_measure_vpwv(self):
        if self.vpwvBtn.isChecked():
            self.flag_vpwv = True
        else:
            self.flag_vpwv = False

    def vpwv_measurement(self):
        if self.dopplerBtn.isChecked():
            # Deliver a single PW to check the pressure and doppler response
            if flag_synthetic:
                time.sleep(self.inflation_time/1000) # inflation duration
            else:
                GPIO.output(24,True)                 # inflation trigger signal
                time.sleep(self.inflation_time/1000) # inflation duration
                GPIO.output(24, False)               # inflation stop
            print('Single PW delivered')
        else:
            # Stop signal acquisition and start PWV measurement
            self.timer.stop()
            self.stop_MCC_scan()
            # Wait the set Delay before sending the trigger signal
            time.sleep(self.delay_vpwv)
            # Start the scan and send the trigger signal for cuff inflation
            self.initialize_MCC_scan('Doppler')
            self.start_MCC_scan()
            if flag_synthetic:
                doppler_new = self.read_synthetic_Tsec(DOPPLER_FS)
            else:
                GPIO.output(24,True)                                            # inflation trigger signal
                time.sleep(self.inflation_time/1000)                            # inflation duration
                GPIO.output(24, False)                                          # inflation stop
                doppler_new, pressure_new = self.read(X_DOPPLER)                # read doppler and pressure
                pressure_new = pressure_new * P_FACTOR
            self.latency, self.profile = PTTcomputation.vPWV_TD_percentage(doppler_new, DOPPLER_FS)
            #self.latency = self.latency - np.where(pressure_new > P_TH)[1]     # cuff pressure is used as reference
            # Update the vPWV arrays, store the doppler epochs, and plot
            now = time.perf_counter()
            if flag_synthetic:
                self.plot3.curveUpdate(np.random.rand(1), now)
                print('Synthetic PW delivered')
                time.sleep(2)
            elif self.latency == self.latency:                                  # check if it's not a NaN
                self.doppler = np.vstack( (self.doppler, np.append(doppler_new, [self.latency, now])) )
                self.plot3.curveUpdate((self.dx/100)/self.latency, now)
                print('PTT = %d ms , D = %d cm , vPWV = %0.3f m/s' % (self.latency*1000, self.dx, (self.dx/100)/self.latency))
            else:
                print('No Pulse Wave peak detected')
            # Re-initialize variables
            self.flag_exp = False
            self.flag_ecg = False
            self.flag_nodeflation = False
            self.deflation_start = time.perf_counter()
            # Restart the singals scan and the Qtimer
            self.t_start = time.perf_counter()
            self.initialize_MCC_scan('Signals')
            self.start_MCC_scan()
            self.timer.start(UPDATE_INTERVAL)

    def record_user_markers(self):
        self.plot3.markersUpdate(time.perf_counter())

####################################### TOGGLE WINDOW SIZE ##########################################

    def toggle_fullscreen(self):
        if self.fullscreenBtn.isChecked():
            self.showFullScreen()
        else:
            self.showNormal()

########################################## END CLASS ################################################

##################################### CLOSE EVENT HANDLER ###########################################

def clean_up():
    Win.timer.stop()
    if flag_synthetic == False and hasattr(Win, 'hat'):
        Win.hat.a_in_scan_stop() 
        Win.hat.a_in_scan_cleanup()
    print('\nAcquisition stopped')
    # Save variables in csv file
    if Win.saveBtn.isChecked() and Win.doppler.ndim > 1:
        with open(os.path.join('/home/leonardo/data_records', Win.filename), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([str(patient_id)])
            writer.writerow([str(Win.dx),"cm"])     # delta X in cm
            writer.writerow(Win.plot3.markers)      # timestamp of user Markers
            writer.writerow(Win.plot3.t)            # timestamp of vPWV measurements
            writer.writerow(Win.plot3.data)         # vPWV values
            writer.writerows(Win.doppler[1:,:])     # doppler epochs
            print('Data saved')

############################################# MAIN ###################################################

if __name__ == "__main__":
    #os.environ["QT_VIRTUALKEYBOARD_LAYOUT_PATH"] = r"G:\My Drive\UniTo\vPWV\Raspy_project\vpwv_mcc\mykeyboardlayouts"
    os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
    App = QApplication(sys.argv)
    App.aboutToQuit.connect(clean_up)
    Dial = DeltaXDialog()
    Win = MainWindow()
    Win.show()
    Dial.show()
    sfmt = QSurfaceFormat()
    sfmt.setSwapInterval(0)
    QSurfaceFormat.setDefaultFormat(sfmt)
    sys.exit(App.exec_())
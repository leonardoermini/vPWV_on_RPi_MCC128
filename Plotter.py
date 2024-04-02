import pyqtgraph as pg
# from PyQt5.QtCore import Qt, QEvent, QRectF
# from PyQt5.QtWidgets import QPinchGesture
import numpy as np
from scipy.signal import stft
from matplotlib.pyplot import get_cmap

class  SignalsPlotter(pg.PlotWidget):
    pg.setConfigOption('background', [36, 42, 56])

    def __init__(self, parent=None, **kargs):
        pg.PlotWidget.__init__(self, **kargs) # consider: super().__init__(*args, **kwargs)
        self.setParent(parent)
    #    self.grabGesture(Qt.GestureType.PinchGesture)

    # def event(self, event):
    #     if event.type() == QEvent.Gesture:
    #         if event.gesture(Qt.PinchGesture):
    #             self.pinchTriggered(event.gesture(Qt.PinchGesture))
    #     return super(SignalsPlotter, self).event(event)
    
    # def pinchTriggered(self, gesture):
    #     if QPinchGesture.ScaleFactorChanged:
    #         sc = 1.001 ** gesture.totalScaleFactor()
    #         center = self.range.center()
    #         w = self.range.width()  / sc
    #         h = self.range.height() / sc
    #         newrange = QRectF(center.x() - (center.x()-self.range.left()) / sc, center.y() - (center.y()-self.range.top()) / sc, w, h)
    #         self.setRange(rect=newrange)

    def setUp(self, curvename, curveunits, curvecolor, X_LEN, SCAN_RATE):
        self.curve = pg.PlotCurveItem(pen=pg.mkPen(curvecolor), name=curvename)
        self.addItem(self.curve)
        self.scatter = pg.ScatterPlotItem()
        self.addItem(self.scatter)
        self.t = np.arange(0, X_LEN/SCAN_RATE, 1/SCAN_RATE)
        self.data = np.full(X_LEN, np.nan)
        self.markers = np.zeros(X_LEN, dtype=bool)
        self.setLabel('left', curvename, units=curveunits)
    
    def setUpSonogram(self, curvename, curvecolor, X_LEN, SCAN_RATE):
        self.sonogram = pg.ImageItem(pen=pg.mkPen(curvecolor), name=curvename)
        self.addItem(self.sonogram)
        lut = self.generatePgColormap('viridis')
        self.sonogram.setLookupTable(lut)
        self.nfft = 512
        self.scan_rate_fft = SCAN_RATE
        self.levels_fft = (-130, -25) # minimum and maximum of 256 rgb to display
        self.data = np.ones(X_LEN)
        f, t, Sxx = stft(self.data, window='hann', fs=self.scan_rate_fft, nperseg=self.nfft, noverlap=self.nfft/2, \
                        boundary=None, scaling='psd')
        arr = 20 * np.log10( np.abs(Sxx) + 1e-12 )
        self.sonogram.setImage(arr.T, levels=self.levels_fft)
        self.sonogram.setRect(0, 0, t[-1], f[-1])
        self.setLabel('left', "Frequency", units='Hz')

    def curveUpdate(self, newdata):
        n = len(newdata)
        self.data = np.roll(self.data, -n)
        if n: self.data[-n:] = newdata
        self.curve.setData(self.t, self.data, antialias=True, connect='all', skipFiniteCheck=False)
    
    def markersUpdate(self, newmarkers):
        n = len(newmarkers)
        self.markers = np.roll(self.markers, -n)
        if n: self.markers[-n:] = newmarkers
        self.scatter.setData(self.t[self.markers], self.data[self.markers], antialias=True, skipFiniteCheck=False)

    def sonogramUpdate(self, newdata):
        n = len(newdata)
        self.data = np.roll(self.data, -n)
        if n: self.data[-n:] = newdata
        _, _, Sxx = stft(self.data, window='hann', fs=self.scan_rate_fft, nperseg=self.nfft, noverlap=self.nfft/2, \
                                boundary=None, scaling='psd')
        arr = 20 * np.log10( np.abs(Sxx) + 1e-12 )
        self.sonogram.setImage(arr.T, levels=self.levels_fft)

    @staticmethod
    def generatePgColormap(cm_name):
        colormap = get_cmap(cm_name)
        colormap._init()
        lut = (colormap._lut * 255).view(np.ndarray)  # Convert matplotlib colormap from 0-1 to 0 -255 for Qt
        return lut

class vpwvPlotter(pg.PlotWidget):
    pg.setConfigOption('background', [36, 42, 56])

    def __init__(self, parent=None, **kargs):
        pg.PlotWidget.__init__(self, **kargs) # consider: super().__init__(*args, **kwargs)
        self.setParent(parent)
    
    def setUp(self, curvename, curvecolor):
        self.setLabel('left', curvename, units='m/s')
        self.setLabel('bottom', 'Time', units='s')
        self.curve = pg.PlotDataItem(pen=pg.mkPen(curvecolor), \
                                     symbol='+', symbolPen='m', name=curvename)
        self.addItem(self.curve)
        self.scatter = pg.ScatterPlotItem(symbol='star', pen='r')
        self.addItem(self.scatter)
        self.t = np.full(0, np.nan)
        self.data = np.full(0, np.nan)
        self.markers = np.zeros(0, dtype=bool)

    def curveUpdate(self, newdata, newtime):
        self.data = np.append(self.data, newdata)
        self.t = np.append(self.t, newtime)
        self.curve.setData(self.t, self.data, antialias=True, connect='all', skipFiniteCheck=False)
    
    def markersUpdate(self, newmarker):
        self.markers = np.append(self.markers, newmarker)
        self.scatter.addPoints(self.markers[-1], np.ones(1)*2, antialias=True, skipFiniteCheck=False)

# vPWV_on_RPi_&_MCC128
A portable device for venous Pulse Wave Velocity measurement

The present code is intended to be used on a Raspberry Pi 4 B+ (Processor: Broadcom BCM2711 quad-core 64 bit ARM Cortex-A72, 1.5 GHz; RAM: 4 GB) equipped with MCC128 DAQ HAT used to acquire, sequentially, the following analogic signals:

- breathing, measured by custom-made chest band integrating a resistive sensor (strain gauge)
- ECG, measured by AD8232 SparkFun Single Lead Heart Rate Monitor
- Doppler shift signal, measured by dedicated US machine

The device final purpose is to control a digital output (3.3 V) which activates a relay (KY-019 5V Relais module) which, in turn, drives a solenoid valve (3V210-08 12VDC 3-Way, Heschen, Zhejiang, China), connecting a compressed air supply (2 bar). In this way a rapid inflation of a cuff wrapped around the limb extremity is achieved, thereby delivering the limb compression that generates a Pulse Wave.

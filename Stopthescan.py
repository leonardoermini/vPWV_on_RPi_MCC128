#This function stop a scan that was remained active after a crash during scripts development

from daqhats import mcc128, OptionFlags, HatIDs, HatError, AnalogInputMode, \
    AnalogInputRange
from daqhats_utils import select_hat_device, enum_mask_to_string, \
    chan_list_to_mask, input_mode_to_string, input_range_to_string

def main():
    address = select_hat_device(HatIDs.MCC_128)
    hat = mcc128(address)
    hat.a_in_scan_stop()
    hat.a_in_scan_cleanup()

if __name__ == '__main__':
    main()
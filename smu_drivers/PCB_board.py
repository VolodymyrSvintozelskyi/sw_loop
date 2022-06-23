
import pyvisa
import numpy as np

class SMU:
    parameters = {
        "threshold": {
            'type': "text"
        },
        "shift": {
            'type': "text"
        },
        "trig_ch": {
            'type': "text"
        },
        "data_ch": {
            'type': "text"
        }
    }

    def __init__(self, port, custom_parameters={}) -> None:
        for k,v in custom_parameters.items():
            setattr(self, k, v['value'])
        self.trig_ch = (self.trig_ch)
        self.data_ch = (self.data_ch)
        self.shift = int(self.shift)
        self.threshold = float(self.threshold)
        print("Custom pars: {}".format(custom_parameters))
        
        self.rm = pyvisa.ResourceManager() 
        self.port = self.rm.open_resource(port)
        self.port.write('*IDN?')
        resp = self.port.read().strip()
        assert resp != "", "Invalid SMU responce"
        print("SMU connected: ", resp)
        self.port.write('DATA:WIDTH 1')
        self.port.write('DATA:ENC RPB') 
        print("SMU ready")

    def applyV(self, v):
        pass
        
    def measureVI(self):
        trig_data = self.acquire(self.trig_ch)
        sig_data = self.acquire(self.data_ch)
        threshold = self.threshold
        rising_edge =  np.argwhere(np.diff(np.sign(trig_data - threshold)) > 0 ).flatten()
        meas_data = sig_data[rising_edge + self.shift]
        return np.mean(meas_data), 0

    def disconnect(self):
        self.port.close()
        print("SMU disconnected")

    def acquire(self, channel):
        try:
            self.port.write("DATA:SOURCE CH" + str(channel))
            ymult = float(self.port.query('WFMPRE:YMULT?'))
            yzero = float(self.port.query('WFMPRE:YZERO?'))
            yoff = float(self.port.query('WFMPRE:YOFF?'))        
            ADC_wave = np.array(self.port.query_binary_values('CURVE?', datatype='B'))
            Volts = (ADC_wave - yoff) * ymult  + yzero
            Volts /= 10 # Yuliia's advice 
            return Volts
        except IndexError:
            return 0
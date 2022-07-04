import pyvisa
import numpy as np
import numpy as np

class SMU:

    stop_measurement_cmd_set = """
SOUR{ch}:VOLT 0
SENS{ch}:CURR:PROT 0.0001
SOUR{ch}:VOLT:RANG:AUTO ON
"""

    start_measurement_cmd_set = """
SOUR{ch}:WAIT:AUTO ON
SENS{ch}:WAIT:AUTO ON

CALC{ch}:MATH:STAT off
CALC{ch}:CLIM:STAT OFF
SENS{ch}:RES:MODE MAN
SOURCE{ch}:SWE:RANG AUTO
SOURCE{ch}:VOLT:RANG:AUTO on
SOURCE{ch}:FUNC PULS
SOURCE{ch}:VOLT {basevoltage}
SOURCE{ch}:VOLT:TRIG {pulsevoltage}
SOUR{ch}:PULS:DEL {pulsedelay}
SOUR{ch}:PULS:WIDT {pulsewidth}
SENS{ch}:CURR:PROT {compliance}
SOUR{ch}:FUNC:MODE VOLT
SOURCE{ch}:VOLT:MODE FIX
TRIG{ch}:TRAN:DEL {measdelay}

FORM REAL,64
FORM:BORD NORM
FORM:ELEM:SENS VOLT,CURR,TIME

SENS{ch}:FUNC:OFF:ALL
SENS{ch}:FUNC:ON "VOLT"
SENS{ch}:VOLT:APER:AUTO OFF
SENS{ch}:VOLT:NPLC {nplc}
SENS{ch}:VOLT:RANG:AUTO ON
SENS{ch}:VOLT:RANG:AUTO:LLIM MIN

TRIG{ch}:ACQ:DEL {measdelay}

SENS{ch}:FUNC:ON "CURR"
SENS{ch}:CURR:APER:AUTO OFF
SENS{ch}:CURR:NPLC {nplc}
SENS{ch}:CURR:RANG:AUTO ON
SENS{ch}:CURR:RANG:AUTO:LLIM 1e-6

TRIG{ch}:ACQ:DEL {measdelay}

SENS{ch}:REM OFF
OUTP{ch}:HCAP OFF

SENS{ch}:VOLT:RANG:AUTO:MODE NORM
SENS{ch}:CURR:RANG:AUTO:MODE NORM
SENS{ch}:VOLT:RANG:AUTO:THR 90
SENS{ch}:CURR:RANG:AUTO:THR 90

OUTP{ch}:FILT ON
OUTP{ch}:FILT:AUTO OFF
OUTP{ch}:FILT:TCON 5e-06

SOUR{ch}:WAIT:GAIN 1
SOUR{ch}:WAIT:OFFS 0
SENS{ch}:WAIT:GAIN 1
SENS{ch}:WAIT:OFFS 0

SOUR{ch}:FUNC:TRIG:CONT OFF

ARM{ch}:ALL:COUN {repeat}
ARM{ch}:ALL:DEL 0
ARM{ch}:LXI:LAN:DIS:ALL
ARM{ch}:ALL:SOUR AINT
ARM{ch}:ALL:TIM MIN
TRIG{ch}:ALL:COUN {var1count}
TRIG{ch}:LXI:LAN:DIS:ALL
TRIG{ch}:ALL:SOUR AINT
TRIG{ch}:ALL:TIM MIN

SOUR{ch}:WAIT ON
SENS{ch}:WAIT ON
OUTP{ch}:STAT ON
STAT:OPER:PTR 7020
STAT:OPER:NTR 7020
STAT:OPER:ENAB 7020
*SRE 128
SYST:TIME:TIM:COUN:RES:AUTO ON

"""


# ARM{ch}:ACQ:DEL {meashold}
# ARM{ch}:TRAN:DEL 0



# TRIG{ch}:TRAN:COUN 2
# TRIG{ch}:ACQ:COUN {measpoints}
# TRIG{ch}:TRAN:DEL 0.01

# TRIG{ch}:TRAN:SOUR TIM
# TRIG{ch}:TRAN:TIM {period}
# TRIG{ch}:ACQ:SOUR TIM
# TRIG{ch}:ACQ:TIM {measinterval}
# SOUR{ch}:WAIT OFF
# SENS{ch}:WAIT OFF




    parameters = {
        "nplc": {
            'type': "text"
        },
        "channel": {
            'type': "text"
        }
    }

    def checkerror(self, suppress_exception = False):
        err = self.inst.query('SYST:ERR:COUN?')
        if (err != '+0'):
            numbers = int(err[1:])
            print('SMU errors:', err)
            for err_n in range(numbers):
                print("Error ", err_n, ":")
                print(self.inst.query("SYST:ERR?"))
            if not suppress_exception:
                raise Exception("SMU Exception")
            else:
                print("SMU errors were suppressed")

    def sendcmd(self, cmd):
        self.inst.write(cmd)
        self.checkerror()
        
    def querycmd(self, cmd):
        resp = self.inst.query(cmd)
        self.checkerror()
        return resp

    def querybincmd(self, cmd):
        resp = self.inst.query_binary_values(cmd, datatype='d', is_big_endian=True)
        self.checkerror()
        return resp

    def getSensData(self):
        res = self.querybincmd("READ:ARR? (@{ch})".format(ch=self.channel))
        formatted_data = []
        for i in range(0,len(res),3):
            formatted_data.append([res[j] for j in range(i,i+3)])
        return formatted_data

    def __init__(self, port, custom_parameters={}) -> None:
        print("SMU connecting: ", port)
        for k,v in custom_parameters.items():
            setattr(self, k, v['value'])
        self.channel = int(self.channel)
        print("Custom pars: ch {}, npls {}".format(self.channel, self.nplc))
        
        self.rm = pyvisa.ResourceManager() 
        self.inst = self.rm.open_resource(port)
        self.inst.read_termination = "\n"
        self.inst.write('*IDN?')
        resp = self.inst.read().strip()
        assert resp != "", "Invalid SMU responce"
        print("SMU connected: ", resp)
        self.checkerror(True)

    def applyV(self, v):
        raise Exception("This function should not be called: applyV(self,v)")

    def configure(self, custom_parameters={}, reset_time=True):
        # custom_parameters["measpoints"] = {"value": int(float(custom_parameters["period"]["value"])/float(custom_parameters["measinterval"]["value"]))}
        for k,v in custom_parameters.items():
            setattr(self, k, v['value'])
        self.channel = int(self.channel)
        start_measurement_cmd = SMU.start_measurement_cmd_set.format(
            ch = self.channel,
            basevoltage = self.basevoltage,
            pulsevoltage = self.pulsevoltage,
            pulsedelay = self.pulsedelay,
            pulsewidth = self.pulsewidth,
            compliance = self.compliance,
            nplc = self.nplc,
            # meascurrrange = self.meascurrrange,
            # meashold = self.meashold,
            # measpoints = self.measpoints,
            # period = self.period,
            # measinterval = self.measinterval,
            repeat = self.repeat,
            measdelay = self.measdelay,
            var1count = self.var1count
        ) 

        self.inst.timeout = int(self.repeat) * int(self.var1count) * (float(self.pulsewidth) + float(self.pulsedelay)) * 1000 * 50 + 10000 

        for cmd in start_measurement_cmd.split("\n"):
            self.sendcmd(cmd)
        if reset_time:
            self.sendcmd("SYST:TIME:TIM:COUN:RES")
        
    def measureVI(self):
        data = []
        data = (self.getSensData())
        status = (self.querycmd("*OPC?"))
        while status != "1":
            status = (self.querycmd("*OPC?"))
        return np.array(data)

    def disconnect(self):
        try:
            for cmd in SMU.stop_measurement_cmd_set.format(self.channel).split("\n"):
                self.sendcmd(cmd)
        except Exception:
            pass
        self.inst.close()
        print("SMU disconnected")
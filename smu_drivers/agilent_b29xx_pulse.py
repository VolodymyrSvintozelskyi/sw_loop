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
CALC{ch}:MATH:STAT off
CALC{ch}:CLIM:STAT OFF
SENS{ch}:RES:MODE MAN
SOURCE{ch}:VOLT:RANG:AUTO on

SOURCE{ch}:VOLT:MODE FIX
SOURCE{ch}:FUNC PULS
SOURCE{ch}:VOLT {basevoltage}
SOURCE{ch}:VOLT:TRIG {pulsevoltage}
SOUR{ch}:PULS:DEL {pulsedelay}
SOUR{ch}:PULS:WIDT {pulsewidth}
SENS{ch}:CURR:PROT {compliance}
SOUR{ch}:FUNC:MODE VOLT
FORM REAL,64
FORM:BORD NORM
FORM:ELEM:SENS VOLT,CURR,TIME
SENS{ch}:FUNC:OFF:ALL
SENS{ch}:FUNC:ON "VOLT"
SENS{ch}:VOLT:APER:AUTO OFF
SENS{ch}:VOLT:NPLC {nplc}
SENS{ch}:FUNC:ON "CURR"
SENS{ch}:CURR:APER:AUTO OFF
SENS{ch}:CURR:NPLC {nplc}
SENS{ch}:CURR:RANG:AUTO OFF
SENS{ch}:CURR:RANG {meascurrrange}
SENS{ch}:REM OFF
OUTP{ch}:HCAP OFF
OUTP{ch}:FILT ON
OUTP{ch}:FILT:AUTO OFF
OUTP{ch}:FILT:TCON 5e-06
SOUR{ch}:FUNC:TRIG:CONT OFF
ARM{ch}:ALL:COUN {repeat}
ARM{ch}:ACQ:DEL {meashold}
ARM{ch}:TRAN:DEL 0
ARM{ch}:LXI:LAN:DIS:ALL
ARM{ch}:ALL:SOUR AINT
ARM{ch}:ALL:TIM MIN
TRIG{ch}:TRAN:COUN 2
TRIG{ch}:ACQ:COUN {measpoints}
TRIG{ch}:TRAN:DEL 0.01
TRIG{ch}:ACQ:DEL 0
TRIG{ch}:TRAN:SOUR TIM
TRIG{ch}:TRAN:TIM {period}
TRIG{ch}:ACQ:SOUR TIM
TRIG{ch}:ACQ:TIM {measinterval}
SOUR{ch}:WAIT OFF
SENS{ch}:WAIT OFF
OUTP{ch}:STAT ON
STAT:OPER:PTR 7020
STAT:OPER:NTR 7020
STAT:OPER:ENAB 7020
*SRE 128
SYST:TIME:TIM:COUN:RES:AUTO ON
SYST:TIME:TIM:COUN:RES"""

    parameters = {
        "nplc": {
            'type': "text"
        },
        "channel": {
            'type': "text"
        }
    }

    def checkerror(self):
        err = self.inst.query('SYST:ERR:COUN?')
        if (err != '+0'):
            numbers = int(err[1:])
            print('SMU errors:', err)
            for err_n in range(numbers):
                print("Error ", err_n, ":")
                print(self.inst.query("SYST:ERR?"))
            raise Exception("SMU Exception")

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

    def applyV(self, v):
        raise Exception("This function should not be called: applyV(self,v)")

    def configure(self, custom_parameters={}):
        custom_parameters["measpoints"] = int(float(custom_parameters["period"])/float(custom_parameters["measinterval"]))
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
            meascurrrange = self.meascurrrange,
            meashold = self.meashold,
            measpoints = self.measpoints,
            period = self.period,
            measinterval = self.measinterval,
            repeat = self.repeat
        ) 

        for cmd in start_measurement_cmd.split("\n"):
            self.sendcmd(cmd)
        
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
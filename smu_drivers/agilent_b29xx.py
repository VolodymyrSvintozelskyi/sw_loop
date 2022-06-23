
# # at start of the sequencer
#    connect()     -> for all items: get and open a port object to communicate with a device
#    initialize()  -> for all items: set all value and configurations to make the device ready for a measurement
   
#        # if a item of the sequencer starts its parameter variation
#        signin()  -> does nothing, but can be used to do something before the parameter variation starts
       
#        # if a new branch is entered and the module was not part of the previous branch
#        configure()  -> changes the configuration of the device
#        poweron()    -> switches the device on
   
#            # for each measurement point
#            # each function is done for all items of the branch before the next function is performed: 
#            start()          -> prepare something before value is applied
#            ----------------------------------------------------------------------------------------------
#            apply()          -> set the new value to a device if supported, only called if sweep value changes
#            reach()          -> wait to reach the new value, start reaching a certain condition,  only called if 'apply' was called previously
#            ----------------------------------------------------------------------------------------------
#            wait hold time       -> sleep any hold time while the setvalues are applied
#            ----------------------------------------------------------------------------------------------
#            adapt()          -> adapt the measurement devices to the new conditions
#            adapt_ready()    -> make sure all device have adapted to the new conditions
#            trigger_ready()  -> make devices ready to be triggered
#            trigger()        -> deprecated: will be continued for a while
#            ----------------------------------------------------------------------------------------------
#            measure()        -> initiate/trigger a measurement, nothing else
#            request_result() -> request a result from the device buffer
#            read_result()    -> read a result from the port buffer
#            ----------------------------------------------------------------------------------------------
#            process_data()   -> process the measured data after the measurement itself has finished
#            call()           -> mandatory: return values to SweepMe! as defined by self.variables
#            ----------------------------------------------------------------------------------------------
#            process()        -> deprecated: will be continued for a while
#            finish()         -> clean up before the next measurement starts 
#            ----------------------------------------------------------------------------------------------
#            wait stop time       -> deprecated from 1.5.5.: sleep any stop time while time while the devices are set to their idlevalues
     
#        #  if a branch is left and the module is not part of the next branch; also called if run is stopped by error
#        poweroff()      -> for all items: switches the device off
#        unconfigure()   -> set value to idlevalue and apply() it
       
#        # if a item of the sequencer finishs its parameter variation
#        signout()  -> does nothing, but can be used to do something after the parameter variation
   
#    # at end for all items of the sequencer; also called if run is stopped by error
#    deinitialize()   -> for all items: reset the status for any other user of the equipment
#    disconnect()     -> for all items: closes the port object

import pyvisa

class EmptyDevice:
    pass

class Device(EmptyDevice):

    multichannel = [" CH1", " CH2"]

    def __init__(self):
        
        EmptyDevice.__init__(self)
        
        self.shortname = "Agilent B29xx"
        
        # remains here for compatibility with v1.5.3
        self.multichannel = [" CH1", " CH2"]
        
        self.variables =["Voltage", "Current"]
        self.units =    ["V", "A"]
        self.plottype = [True, True] # True to plot data
        self.savetype = [True, True] # True to save data

        self.port_manager = True
        self.port_types = ["USB", "GPIB"]
        
        # self.port_properties = { "timeout": 10,
                                 # }
                                 
        self.commands = {
                        "Voltage [V]" : "VOLT",
                        "Current [A]" : "CURR",
                        }
                                 
    def set_GUIparameter(self):
        
        GUIparameter = {
                        "SweepMode" : ["Voltage [V]", "Current [A]"],
                        "RouteOut": ["Front", "Rear"],
                        "Speed": ["Fast", "Medium", "Slow"],
                        "Compliance": 100e-6,
                        #"Average": 1, # not yet supported
                        }
                        
        return GUIparameter
                                 
    def get_GUIparameter(self, parameter = {}):
        self.four_wire = parameter['4wire']
        self.route_out = parameter['RouteOut']
        self.source = parameter['SweepMode']
        self.protection = parameter['Compliance']
        self.speed = parameter['Speed']
        self.average = int(parameter['Average'])
        
        if self.average < 1:
            self.average = 1
        if self.average > 100:
            self.average = 100
            
        self.device = parameter['Device']
        self.channel = self.device[-1]
        
        
    def initialize(self):
        # once at the beginning of the measurement
        self.port.write("*RST")
        ##from Keithley2400##  self.port.write("status:preset" )
        ##from Keithley2400##  self.port.write("*CLS") # reset all values
        
        self.port.write("SYST:BEEP:STAT OFF")     # control-Beep off
        
        self.port.write(":SYST:LFR 50") # LineFrequency = 50 Hz
        
        self.port.write(":OUTP%s:PROT ON" % self.channel)  # enables  over voltage / over current protection

            
    def configure(self):
    
        
        if self.source == "Voltage [V]":
            self.port.write(":SOUR%s:FUNC VOLT" % self.channel)                  
            # sourcemode = Voltage
            self.port.write(":SOUR%s:VOLT:MODE FIX" % self.channel)
            # sourcemode fix
            self.port.write(":SENS%s:FUNC \"CURR\"" % self.channel)              
            # measurement mode
            self.port.write(":SENS%s:CURR:PROT %s" % (self.channel, self.protection))
            # Protection with Imax
            self.port.write(":SENS%s:CURR:RANG:AUTO ON" % self.channel)
            # Autorange for current measurement
           
      
        if self.source == "Current [A]":
            self.port.write(":SOUR%s:FUNC CURR" % self.channel)                  
            # sourcemode = Voltage
            self.port.write(":SOUR%s:CURR:MODE FIX" % self.channel)
            # sourcemode fix		
            self.port.write(":SENS%s:FUNC \"VOLT\"" % self.channel)              
            # measurement mode
            self.port.write(":SENS%s:VOLT:PROT " % (self.channel, self.protection))
            # Protection with Imax
            self.port.write(":SENS%s:VOLT:RANG:AUTO ON" % self.channel)
            # Autorange for voltage measurement
               
        if self.speed == "Fast":
            self.nplc = "0.1"
        if self.speed == "Medium":
            self.nplc = "1.0"
        if self.speed == "Slow":
            self.nplc = "10.0"
 
        self.port.write(":SENS%s:CURR:NPLC %s" % (self.channel, self.nplc))
        self.port.write(":SENS%s:VOLT:NPLC %s" % (self.channel, self.nplc))
        
        self.port.write(":SENS%s:CURR:RANG:AUTO:MODE RES" % (self.channel))
        
        # ioObj.WriteString(":SENS:CURR:RANG:AUTO:MODE NORM") Normal
        # ioObj.WriteString(":SENS:CURR:RANG:AUTO:THR 80")
        # ioObj.WriteString(":SENS:CURR:RANG:AUTO:MODE RES") Resolution
        # ioObj.WriteString(":SENS:CURR:RANG:AUTO:THR 80")
        # ioObj.WriteString(":SENS:CURR:RANG:AUTO:MODE SPE") Speed
        
        # 4-wire sense
        if self.four_wire:
            self.port.write("SYST:REM ON")
        else:
            self.port.write("SYST:REM OFF")
        
        """
        # averaging
        self.port.write(":SENS:AVER:TCON REP")   # repeatedly take average
        if self.average > 1:
            self.port.write(":SENS:AVER ON") 
            self.port.write(":SENSe:AVER:COUN %i" % self.average)   # repeatedly take average
        else:
            self.port.write(":SENS:AVER OFF")
            self.port.write(":SENSe:AVER:COUN 1")  
        """

           
        self.port.write(":OUTP%s:PROT ON" % self.channel)    
        #self.port.write(":OUTP:LOW GRO") # LowGround
        #self.port.write(":OUTP:HCAP ON") # High capacity On
     
    def deinitialize(self):
        if self.four_wire:
            self.port.write("SYST:REM OFF")
        
        self.port.write(":SENS%s:CURR:NPLC 1" % self.channel)
        self.port.write(":SENS%s:VOLT:NPLC 1" % self.channel)
        
       
        
        # self.port.write(":SENS:AVER OFF")
        # self.port.write(":SENSe:AVER:COUN 1")  

    def poweron(self):
        self.port.write(":OUTP%s ON" % self.channel)
        
    def poweroff(self):
        self.port.write(":OUTP%s OFF" % self.channel)
                        
    def apply(self):
    
        self.port.write(":SOUR%s:%s  %s" % (self.channel, self.commands[self.source], self.value))     # set source
         
    def trigger(self):
        pass
                       
    def measure(self):    
        pass                              

    def call(self):
        self.port.write(":MEAS? (@%s)" % self.channel) 
    
        answer = self.port.read()
        
        # print(answer)
        
        values = answer.split(",")
        
        voltage = float(values[0])
        current =  float(values[1])
        
        return [voltage, current]
    
        
    def finish(self):
        pass
        
        
class SMU(Device):
    parameters = {
        "nplc": {
            'type': "text"
        },
        "channel": {
            'type': "text"
        }
    }

    def __init__(self, port, custom_parameters={}) -> None:
        print("SMU connecting: ", port)
        super().__init__()
        gui_parameters = {
            '4wire': False,
            'RouteOut': "???",
            'SweepMode': "Voltage [V]",
            'Compliance': 0.01,
            'Speed': 'MANUAL',
            'Average': 0,
            'Device': [
                2# channel
            ]
        }
        self.get_GUIparameter(gui_parameters)
        for k,v in custom_parameters.items():
            setattr(self, k, v['value'])
        self.channel = int(self.channel)
        print("Custom pars: ch {}, npls {}".format(self.channel, self.nplc))
        self.rm = pyvisa.ResourceManager() 
        self.port = self.rm.open_resource(port)
        self.port.write('*IDN?')
        resp = self.port.read().strip()
        assert resp != "", "Invalid SMU responce"
        print("SMU connected: ", resp)
        self.initialize()
        self.configure()
        self.poweron()
        print("SMU ready")

    def applyV(self, v):
        self.value = v
        self.apply()
        
    def measureVI(self):
        return self.call()

    def disconnect(self):
        self.poweroff()
        self.deinitialize()
        self.port.close()
        print("SMU disconnected")
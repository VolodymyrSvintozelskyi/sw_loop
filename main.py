# import eel
import Run
import numpy as np

run = None

def start_run(configuration):
    print("Start run")
    global run
    if (run is None) or (not run.is_alive()):
        run = Run.Run()
        run.start_run(configuration)
        return "ok"
    else:
        return "Thread is alredy alive"

import json
 
# Opening JSON file
with open('conf.json') as json_file:
    conf = json.load(json_file)

conf["Vr_prof"] = -0.5  # Referce voltage
conf["Vf_prof_arr"] = np.arange(0,1 + 0.1,0.25).tolist()  # Array of forward voltages. Generate array from 0 to 1 (incl) with 0.25 step
conf["Duty_cycles"] = [0.1,0.25,0.5,0.75] # Array of duty cycles (D). D = Tr / Period. Tr - time for reverse voltage, Period = 100 ms?

start_run(conf)
run.join()
print("Main thread exit")
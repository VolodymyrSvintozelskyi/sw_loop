import threading as T
import numpy as np
import time
from pathlib import Path
from datetime import datetime
import traceback
import serial
import importlib.util
import json

class COMM:
    def __init__(self, port) -> None:
        print("COMM connecting... ", port)
        self.port = serial.Serial(port,115200, timeout =10)
        resp = self.port.readline().decode().strip()
        assert resp == "Ready!", "Invalid COMM responce"
        print("COMM connected")
    def wait_responce(self):
        answered = False
        start_time = time.time()
        while (self.port.in_waiting > 0) or not answered:
            resp = self.port.readline().decode().strip()
            if resp == '0' or resp == '1':
                answered = True
            else:
                print(resp)
            if (time.time() - start_time) > 5:
                self.disconnect()
                raise TimeoutError("COMM timeout exception")
    def setPin(self, pin=""):
        self.port.write(pin.encode())
        self.wait_responce()
    def setDelay(self, delay):
        self.port.write("setdelay {}".format(delay).encode())
        self.wait_responce()
    def disconnect(self):
        self.port.close()
        print("COMM disconnected")

class Run(T.Thread):
    def __init__(self, update_signal_chart = lambda *args: None, send_stop_run = lambda *args:None):
        super(Run, self).__init__(daemon=True)
        print("Thread init..")
        self._stop_event = T.Event()
        self.update_signal_chart = update_signal_chart
        self.send_stop_run = send_stop_run
        self.pixel_time_left = -1
        self.total_time_left = -1
        self.dashboard = False

    def start_run(self,configuration):
        print("Thread start..")
        self.conf = configuration
        self._stop_event.clear()
        self.outputfolder = "./output/{}".format(  configuration['output_folder'].format(timestamp=datetime.now().strftime("%m_%d_%Y-%H_%M_%S")))
        Path(self.outputfolder).mkdir(parents=True, exist_ok=True)
        with open("{}/conf.json".format(self.outputfolder), "w") as write_file:
            json.dump(configuration, write_file, indent=4)
        self.start()

    def stop_run(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        print("Thread started..")
        smu = None
        led = None
        comm = None
        try:
            print("Instruments configuration...")
            smu_mod_spec=importlib.util.spec_from_file_location("{}".format(self.conf["smu_type"]),"smu_drivers/{}.py".format(self.conf["smu_type"]))
            smu_mod = importlib.util.module_from_spec(smu_mod_spec)
            smu_mod_spec.loader.exec_module(smu_mod)

            led_mod_spec=importlib.util.spec_from_file_location("{}".format(self.conf["led_type"]),"led_drivers/{}.py".format(self.conf["led_type"]))
            led_mod = importlib.util.module_from_spec(led_mod_spec)
            led_mod_spec.loader.exec_module(led_mod)
            
            
            led = led_mod.LED(self.conf["led_port"])
            smu = smu_mod.SMU(self.conf["smu_port"], self.conf["smu_custom_pars"])
            comm = COMM(self.conf["comm_port"])
            comm.setDelay(self.conf["comm_relay_delay"])
            
            print("Instruments ready")
            stop_run_flag = False

            Vr_prof = self.conf["Vr_prof"]
            Vf_prof_arr = self.conf["Vf_prof_arr"]   # generate array from 0 to 1 (incl) with 0.25 step
            Duty_cycles = self.conf["Duty_cycles"]  # Tr/Tf
            Period = self.conf["smu_t_step"]
            
            for Vf_prof in Vf_prof_arr:
                for Duty_cycle in Duty_cycles:
                    Tr = Duty_cycle * Period
                    Tf = (1-Duty_cycle) * Period
                    print("Start with Vr_prof: {} Vf_prof: {} Tr: {} Tf: {}".format(Vr_prof, Vf_prof, Tr, Tf))

                    for p_iter, pixel in enumerate(self.conf["pixel_loop"]["loop"]):
                        self.current_pixel = pixel
                        comm.setPin(pixel["ext"] + pixel["inn"])
                        led.setCurrent(pixel["curr"])
                        pixel_start_time = time.time()
                        # self.update_signal_chart(pixel_no = p_iter)
                        newpixel_flag = True

                        print("Pixel {}: I={}".format(p_iter, pixel['curr']))
                        
                        with open("{}/{}{}.txt".format(self.outputfolder, pixel["ext"], pixel["inn"]), 'a') as f:
                            print("#pixel_time[s]\tV[V]\tI[A]",file=f)
                            while time.time() - pixel_start_time < self.conf["smu_t_total"]:
                                for v_iter,volt_norm in enumerate(np.array(self.conf["smu_v_profile"])):
                                    volt = Vf_prof if volt_norm == 1 else (Vr_prof if volt_norm == -1 else 0) 
                                    smu.applyV(volt)
                                    time_to_sleep = Tf if volt_norm == 1 else (Tr if volt_norm == -1 else Period) 
                                    time.sleep(time_to_sleep)
                                    real_v,i = smu.measureVI()
                                    print("{}\t{}\t{}".format(time.time()-pixel_start_time, real_v, i), file=f)
                                    print(volt,time_to_sleep)
                                    if (self._stop_event.is_set()):
                                        stop_run_flag = True
                                        break
                                    # if self.conf["smu_recovery_enable"] and (i > self.conf["smu_rec_thresh"]):
                                    #     break
                                else:
                                    smu.applyV(0)
                                    continue
                                break
                            else:
                                print("Recovery")
                            if stop_run_flag:
                                break
                            # RECOVERY
                            # print("RECOVERY")
                            recovery_start_time = time.time()
                            while time.time() - recovery_start_time < self.conf["smu_t_total_rec"]:
                                for v_iter,volt in enumerate(np.array(self.conf["smu_v_profile_rec"])* self.conf["smu_v_factor_rec"]):
                                    smu.applyV(volt)
                                    time.sleep(self.conf["smu_t_step_rec"])
                                    real_v,i = smu.measureVI()
                                    print("{}\t{}\t{}".format(time.time()-pixel_start_time, real_v, i), file=f)
                                    self.pixel_time_left = max((len(self.conf["smu_v_profile_rec"]) - v_iter) * self.conf["smu_t_step_rec"], self.conf["smu_t_total_rec"] - (time.time() - recovery_start_time))
                                    self.total_time_left = (len(self.conf["pixel_loop"]["loop"]) - p_iter - 1) * max(len(self.conf["smu_v_profile"])*  self.conf["smu_t_step"], self.conf["smu_t_total"]) + self.pixel_time_left
                                    self.update_signal_chart(real_v,i, p_iter, newpixel_flag)
                                    newpixel_flag = False
                                    if (self._stop_event.is_set()):
                                        stop_run_flag = True
                                        break
                                else:
                                    smu.applyV(0)
                                    continue
                                break
                            else:
                                continue
                            break

            self.send_stop_run()
            smu.disconnect()
            led.disconnect()
            comm.disconnect()
            print("Completed!")
        except Exception as e:
            self.send_stop_run(False, "Runtime exception {}: {}".format(type(e).__name__, e))
            print(traceback.format_exc())
            if not (smu is None): 
                try:
                    smu.disconnect()
                except Exception:
                    print(traceback.format_exc())
            if not (led is None): 
                try:
                    led.disconnect()
                except Exception:
                    print(traceback.format_exc())
            if not (comm is None):
                try: 
                    comm.disconnect()
                except Exception:
                    print(traceback.format_exc())
            
        
                
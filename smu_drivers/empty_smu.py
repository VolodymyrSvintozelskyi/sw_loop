import imp
from random import random
import random

class SMU:
    parameters = {
        "test_par": {
            "type": "text"
        }
    }

    def __init__(self, port, custom_parameters = {}) -> None:
        print("SMU open: ", port)
        print("Custom parameters: ", custom_parameters)

    def applyV(self, v):
        print("V applied")
        
    def measureVI(self):
        curr = random.random()
        return [random.random(), curr]

    def disconnect(self):
        print("SMU switched off")
import random
import time

class PLCDataBlocks:
    def __init__(self):
        self.DB1 = {
            "Temperature": 22.5,
            "Pressure": 1.02,
            "Motor1_Running": False,
            "Motor2_Running": True
        }
        self.DB10 = {
            "Level": 74.0,
            "Valve_Open": False
        }
        self.DB100 = {
            "CPU_Load": 8.5,
            "Scan_Time": 12.3,
            "Error_Code": 0
        }

    def cycle_update(self):
        # Simulate real PLC behavior
        self.DB1["Temperature"] += random.uniform(-0.1, 0.1)
        self.DB1["Pressure"] += random.uniform(-0.01, 0.01)

        self.DB10["Level"] += random.uniform(-1.0, 1.0)
        self.DB10["Valve_Open"] = random.choice([True, False])

        self.DB100["CPU_Load"] = random.uniform(5, 40)
        self.DB100["Scan_Time"] = random.uniform(8, 15)

    def dump(self):
        return {
            "DB1": self.DB1,
            "DB10": self.DB10,
            "DB100": self.DB100,
        }

          

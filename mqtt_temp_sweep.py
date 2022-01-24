
import miniconf
import asyncio
import time
import numpy as np
from matplotlib import pyplot as plt
from pydwf import DwfLibrary, PyDwfError
from pydwf.utilities import openDwfDevice

prefix = "dt/sinara/thermostat-mqtt/80-1f-12-63-84-1a"
broker = "10.42.0.1"

# thermostat settings



# sweep settings
temp_start = 20    # starting temp in °C
temp_stop = 30     # stop temp 
step = 0.5         # temperature steps

async def conf_temp(temp):
    """asynchronous helper to send an miniconf command"""
    interface = await miniconf.Miniconf.create(prefix, broker)
    await interface.command("pidsettings/0/target", temp)


    
def main():

    print("initializing temp to ", temp_start)
    asyncio.run(conf_temp(temp_start))
    time.sleep(10)
    print("sweep start")
    temp_range = np.arange(temp_start, temp_stop, step)
    for temp in temp_range:
        asyncio.run(conf_temp(temp))
        time.sleep(5)

    print("done")

if __name__ == "__main__":
    main()
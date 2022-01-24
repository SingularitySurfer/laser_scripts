
import miniconf
import asyncio
import time
import csv
import numpy as np
from matplotlib import pyplot as plt
from pydwf import DwfLibrary, PyDwfError
from pydwf.utilities import openDwfDevice


# thermostat settings
prefix = "dt/sinara/thermostat-mqtt/80-1f-12-63-84-1a"
broker = "10.42.0.1"

# controller settings for LUCENT D2525P37
p_gain = 10
i_gain = 2
max_i_neg = 0.1
max_i_pos = 0.3

# sweep settings
temp_start = 20    # starting temp in °C
temp_stop = 40     # stop temp 
step = 0.5         # temperature steps


async def conf_temp(temp):
    """asynchronous helper to send an miniconf command"""
    interface = await miniconf.Miniconf.create(prefix, broker)
    await interface.command("pidsettings/0/target", temp)

async def setup_thermostat():
    interface = await miniconf.Miniconf.create(prefix, broker)
    await interface.command("pidsettings/0/max_i_pos", max_i_pos)
    await interface.command("pidsettings/0/max_i_neg", max_i_neg)
    await interface.command("pidsettings/0/pid/0", p_gain)
    await interface.command("pidsettings/0/pid/1", i_gain)
    await interface.command("engage_iir/0", True)


def main():

    dwf = DwfLibrary()

    with openDwfDevice(dwf) as device:

        inp = device.analogIn
        inp.reset()

        print("setup thermostat")
        asyncio.run(setup_thermostat())
        print("initializing temp to ", temp_start)
        asyncio.run(conf_temp(temp_start))


        print("sweep start")
        temp_range = np.arange(temp_start, temp_stop, step)

        fig, ax = plt.subplots()
        
        f = open('data.csv', 'w')
        writer = csv.writer(f)
        v = []
        for temp in temp_range:
            asyncio.run(conf_temp(temp))
            time.sleep(5)
            inp.status(False)
            print("analog input: {}", inp.statusSample(0))
            v.append(inp.statusSample(0))
            writer.writerow([inp.statusSample(0)])
            fig.canvas.draw()
            ax.plot(v)
            plt.pause(0.0001)
            fig.canvas.flush_events()

        f.close()
        print("done")


if __name__ == "__main__":
    main()
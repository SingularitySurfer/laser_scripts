
import miniconf
from gmqtt import Client as MqttClient
import json
import asyncio
import time
import csv
import numpy as np
from matplotlib import pyplot as plt
from pydwf import DwfLibrary, PyDwfError
from pydwf.utilities import openDwfDevice


# thermostat settings
PREFIX = "dt/sinara/thermostat-mqtt/80-1f-12-63-84-1a"
BROKER = "10.42.0.1"

# controller settings for LUCENT D2525P37
P_GAIN = 10
I_GAIN = 2
MAX_I_NEG = 0.1
MAX_I_POS = 0.3
MAXWAIT = 1000      # Maximum waiting time for temp to settle
EM = 0.001          # Error margin for temp settle

# sweep settings
TEMP_START = 20    # starting temp in °C
TEMP_STOP = 40     # stop temp 
STEP = 0.5         # temperature steps


async def conf_temp(temp):
    """asynchronous helper to send an miniconf command"""
    interface = await miniconf.Miniconf.create(PREFIX, BROKER)
    await interface.command("pidsettings/0/target", temp)

async def setup_thermostat():
    interface = await miniconf.Miniconf.create(PREFIX, BROKER)
    await interface.command("pidsettings/0/max_i_pos", MAX_I_POS)
    await interface.command("pidsettings/0/max_i_neg", MAX_I_NEG)
    await interface.command("pidsettings/0/pid/0", P_GAIN)
    await interface.command("pidsettings/0/pid/1", I_GAIN)
    await interface.command("engage_iir/0", True)

class TelemetryReader:
    """ Helper utility to read telemetry. """

    @classmethod
    async def create(cls, prefix, broker, queue):
        """Create a connection to the broker and an MQTT device using it."""
        client = MqttClient(client_id='')
        await client.connect(broker)
        return cls(client, prefix, queue)

    def __init__(self, client, prefix, queue):
        """ Constructor. """
        self.client = client
        self._telemetry = []
        self.client.on_message = self.handle_telemetry
        self._telemetry_topic = f'{prefix}/telemetry'
        self.client.subscribe(self._telemetry_topic)
        self.queue = queue

    def handle_telemetry(self, _client, topic, payload, _qos, _properties):
        """ Handle incoming telemetry messages over MQTT. """
        assert topic == self._telemetry_topic
        self.queue.put_nowait(json.loads(payload))

def main():

    dwf = DwfLibrary()

    with openDwfDevice(dwf) as device:

        inp = device.analogIn
        inp.reset()

        print("setup thermostat")
        asyncio.run(setup_thermostat())
        print("initializing temp to ", TEMP_START)
        asyncio.run(conf_temp(TEMP_START))


        print("sweep start")
        temp_range = np.arange(TEMP_START, TEMP_STOP, STEP)

        fig, ax = plt.subplots()
        ax.set_title("")

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
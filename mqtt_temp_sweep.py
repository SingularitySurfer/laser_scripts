
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
MAX_I_NEG = 0.3
MAX_I_POS = 0.3
MAXWAIT = 1000      # Maximum waiting time for temp to settle in periods
EM = 0.001          # Error margin for temp settle in °C
# Number of periods where temp has to be in margin to be considered settled
P_SETTLE = 5

# sweep settings
TEMP_START = 20    # starting temp in °C
TEMP_STOP = 40     # stop temp
STEP = 0.5         # temperature steps


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

    async def get_tele(telemetry_queue):
        latest_values = await telemetry_queue.get()
        return [latest_values['adcs'][0], latest_values['dacs'][0], latest_values['adcs'][1]]


async def get_tele(telemetry_queue):
    latest_values = await telemetry_queue.get()
    return [latest_values['adcs'][0], latest_values['dacs'][0], latest_values['adcs'][1]]


def set_laser_temp(temp):
    telemetry_queue = asyncio.LifoQueue()

    async def telemetry():
        await TelemetryReader.create(PREFIX, BROKER, telemetry_queue)
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    telemetry_task = asyncio.Task(telemetry())

    async def set_and_wait_settle():
        interface = await miniconf.Miniconf.create(PREFIX, BROKER)

        await interface.command('pidsettings/0/target', temp, retain=False)

        data = []
        for i in range(MAXWAIT):
            data.append(await get_tele(telemetry_queue))
            print(f'temp: {data[i][0]}')
            if P_SETTLE < len([x[0] for x in data[-20:] if (x[0] > (temp-EM)) and (x[0] < (temp+EM))]):
                break

        telemetry_task.cancel()

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(set_and_wait_settle())


def main():

    dwf = DwfLibrary()

    with openDwfDevice(dwf) as device:

        inp = device.analogIn
        inp.reset()

        print("setup thermostat")
        loop = asyncio.get_event_loop()
        temp = loop.run_until_complete(setup_thermostat())

        print("initializing temp to ", TEMP_START)
        set_laser_temp(TEMP_START)

        print("sweep start")
        temp_range = np.arange(TEMP_START, TEMP_STOP, STEP)

        fig, ax = plt.subplots()
        ax.set_title("")

        f = open('data.csv', 'w')
        writer = csv.writer(f)
        v = []
        for temp in temp_range:
            set_laser_temp(temp)
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

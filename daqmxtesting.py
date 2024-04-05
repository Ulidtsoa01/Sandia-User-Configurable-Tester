import nidaqmx
from nidaqmx import *

local_system = nidaqmx.system.System.local()
print(local_system)

#local_system.devices is a list of all attached devices (that are visible on nimax)
'''
for device in local_system.devices:
    print(
        "Device Name: {0}, Product Category: {1}, Product Type: {2}".format(
            device.name, device.product_category, device.product_type
        )
    )
'''
for device in local_system.devices:
    for chan in device.ai_physical_chans:
        print(chan.name)
    for chan in device.ao_physical_chans:
        print(chan.name)
    #print(device.terminals)

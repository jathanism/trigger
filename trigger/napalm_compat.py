"""
Integration of Trigger + NAPALM drivers
"""

from napalm import get_network_driver


def get_driver_for_netdevice(device):
    vendor_name = device.vendor.name
    if vendor_name == 'cisco':
        vendor_name = 'ios'

    driver = get_network_driver(vendor_name)

    return driver

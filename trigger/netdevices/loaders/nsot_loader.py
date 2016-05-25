# -*- coding: utf-8 -*-

"""
Loader for Trigger NetDevices using NSoT API.

Right now this loads ALL devices ALL the time, which scales very poorly with
the number of devices and attributes in NSoT.

Note that ``NETDEVICES_SOURCE`` is ignored because the settings from your
``~/.pynsotrc``.

To use this:

1. Ensure that this module is in your ``PYTHONPATH``  and then add it to
``settings.NETDEVICES_LOADERS``, for example::

    NETDEVICES_LOADERS = ('nsot_loader.NsotLoader',)

Other stuff:

- There is little to no error-handling.
- Authentication/credentials defaults to whatever is used by pynsot (e.g.
  (``~/.pynsotrc``)
"""

from __future__ import unicode_literals

# from dropbox import trigger
from trigger.netdevices.loader import BaseLoader
from trigger.exceptions import LoaderFailed

try:
    # import nsot_client as pynsot
    import pynsot
except ImportError:
    PYNSOT_AVAILABLE = False
else:
    PYNSOT_AVAILABLE = True


__author__ = 'jathan@gmail.com'
__version__ = '0.2'


# Map NSoT fields to ones that Trigger requires or uses.
TRANSFORM_FIELDS = {
    # 'hostname': 'nodeName',
    'hw_type': 'deviceType',
    'metro': 'site',
    'row': 'coordinate',
    'vendor': 'manufacturer',
}

# Whether to force adminStatus='PRODUCTION'
FORCE_PRODUCTION = True

# Load the devices lazily (e.g. not until looked up)
LAZY_LOAD = True
# LAZY_LOAD = False


class NsotLoader(BaseLoader):
    """
    Wrapper for loading metadata via NSoT.

    Note that ``NETDEVICES_SOURCE`` is ignored because the settings from your
    ``~/.pynsotrc``.
    """
    is_usable = PYNSOT_AVAILABLE

    def get_data(self, url=None, lazy=None):
        api_client = pynsot.client.get_api_client()
        self.client = api_client.sites(api_client.default_site)

        if lazy is None:
            lazy = LAZY_LOAD

        if lazy:
            return []

        self._devices = self.client.devices.get()
        return self.transform_devices(self._devices)

    def transform_devices(self, devices):
        return [self.transform_device(device) for device in devices]

    def transform_device(self, device):
        """Transform the fields if they are present."""
        device['nodeName'] = device['hostname']
        attributes = device.pop('attributes')

        # If this is adminStatus, change the value to something Trigger
        # expects.
        if FORCE_PRODUCTION or attributes.get('monitor') != 'ignored':
            admin_val = 'PRODUCTION'
        else:
            admin_val = 'NON-PRODUCTION'
        device['adminStatus'] = admin_val

        # Fixups
        for key, val in attributes.iteritems():
            # Include mapped keys for Trigger semantics
            mapped_key = TRANSFORM_FIELDS.get(key, None)  # KEY? KEY. KEY!

            # Trigger expects required field values to be uppercase
            if mapped_key is not None:
                device[mapped_key] = val.upper()

            # Trigger also has a baked-in "make" field
            if key == 'model':
                device['make'] = val

            device[key] = val

        from trigger.netdevices import NetDevice
        return NetDevice(data=device)

    def transform_fields(self, devices):
        """Transform the fields if they are present."""
        for device in devices:
            device['nodeName'] = device['hostname']
            attributes = device.pop('attributes')

            # If this is adminStatus, change the value to something Trigger
            # expects.
            if FORCE_PRODUCTION or attributes.get('monitor') != 'ignored':
                admin_val = 'PRODUCTION'
            else:
                admin_val = 'NON-PRODUCTION'
            device['adminStatus'] = admin_val

            # Fixups
            for key, val in attributes.iteritems():
                # Include mapped keys for Trigger semantics
                mapped_key = TRANSFORM_FIELDS.get(key, None)  # KEY? KEY. KEY!

                # Trigger expects required field values to be uppercase
                if mapped_key is not None:
                    device[mapped_key] = val.upper()

                # Trigger also has a baked-in "make" field
                if key == 'model':
                    device['make'] = val

                device[key] = val

        return devices

    def load_data_source(self, url, **kwargs):
        try:
            return self.get_data(url)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (url, err))

    def find(self, key):
        # import ipdb; ipdb.set_trace()
        try:
            device = self.client.devices(key).get()
        except:
            raise KeyError(key)
        else:
            return self.transform_device(device)

    def all(self):
        if hasattr(self, '_devices'):
            return self._devices
        return self.get_data(lazy=False)

    def match(self, **kwargs):
        query = kwargs['query']
        devices = self.client.devices.query.get(query=query)
        return self.transform_devices(devices)


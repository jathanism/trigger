from __future__ import unicode_literals

"""
Loader for Trigger NetDevices using NSoT API.

Right now this loads ALL devices ALL the time, which scales very poorly with
the number of devices and attributes in NSoT.

To use this:

1. Set ``settings.NETDEVICES_SOURCE`` the URL to your NSoT instance, for
   example::

    NETDEVICES_SOURCE = 'http://host:port/api'

2. Ensure that this module is in your ``PYTHONPATH``  and then add it to
``settings.NETDEVICES_LOADERS``, for example::

    NETDEVICES_LOADERS = ('nsot_loader.NsotLoader',)

Other stuff:

- There is little to no error-handling.
- Authentication/credentials defaults to whatever is used by pynsot (e.g.
  (``~/.pynsotrc``)
"""

__author__ = 'Jathan McCollum'
__email__ = 'jathan@gmail.com'
__version__ = '0.1'


from trigger.netdevices.loader import BaseLoader
from trigger.exceptions import LoaderFailed
try:
    import pynsot
except ImportError:
    PYNSOT_AVAILABLE = False
else:
    PYNSOT_AVAILABLE = True


# Field mappings from NSoT to Trigger to transform
TRANSFORM_FIELDS = {
    'hostname': 'nodeName',
    'hw_type': 'deviceType',
    'vendor': 'manufacturer',
    'monitored': 'adminStatus',
}


class NsotLoader(BaseLoader):
    """
    Wrapper for loading metadata via NSoT.

    To use this define ``NETDEVICES_SOURCE`` in this format::

        http://host:port/api
    """
    is_usable = PYNSOT_AVAILABLE

    def get_data(self, url):
        client = pynsot.client.get_api_client()
        site = client.sites(client.default_site)
        result = site.devices.get()
        devices = result['data']['devices']

        return self.transform_fields(devices)

    def transform_fields(self, data):
        """Transform the fields if they are present"""
        for d in data:
            d.update(d.pop('attributes'))  # Merge in attrs
            for old, new in TRANSFORM_FIELDS.items():
                # old_value = d.get(old, None)
                old_value = d.pop(old, None)
                if old_value is not None:
                    d[new] = old_value

                    # If the tag is monitored, set adminStatus
                    if new == 'adminStatus':
                        d[new] = 'PRODUCTION'
        return data

    def load_data_source(self, url, **kwargs):
        try:
            return self.get_data(url)
        except Exception as err:
            raise LoaderFailed("Tried %r; and failed: %r" % (url, err))
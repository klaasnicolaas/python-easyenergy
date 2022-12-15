"""Exceptions for easyEnergy."""


class EasyEnergyError(Exception):
    """Generic easyEnergy exception."""


class EasyEnergyConnectionError(EasyEnergyError):
    """easyEnergy - connection exception."""


class EasyEnergyNoDataError(EasyEnergyError):
    """easyEnergy - no data exception."""

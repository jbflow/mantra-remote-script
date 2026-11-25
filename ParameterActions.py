import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from .utils import *
from .constants import *


class ParameterActions(ControlSurfaceComponent):
    __module__ = __name__

    def __init__(self, c_instance):
        ControlSurfaceComponent.__init__(self, c_instance)
        self._c_instance = c_instance
        self.verbs = { VERBS['increase']: self.increase_parameter,
                       VERBS['decrease']: self.decrease_parameter,
                       VERBS['set']: self.set_parameter
                       }

    def get_action(self, **kwargs):
        track_byte, device_byte, parameter_byte, action, amount, unit = convert_bytes(kwargs['noun_adj'][1:-6]) - 1, \
                                                                        convert_bytes(kwargs['noun_adj'][4:-3]) - 1, \
                                                                        convert_bytes(kwargs['noun_adj'][7:]) - 1, \
                                                                        kwargs['verb'], convert_bytes(kwargs['adverb']), \
                                                                        EXTRACT_UNITS[kwargs['units']]
        param, step = self.get_parameter(track_byte, device_byte, parameter_byte)
        return self.verbs[action](param, step, amount, unit)
    



    def get_parameter(self, track_byte, device_byte, parameter_byte):
        if device_byte == 16382:
            device = self.song().tracks[track_byte].mixer_device
            params = [device.volume, device.panning] + list(device.sends)
            param = params[parameter_byte]
        else: 
            device = self.song().tracks[track_byte].devices[device_byte]
            param = device.parameters[parameter_byte]
        step = (param.max - param.min) / 128
        return param, step

    @undo_step
    def increase_parameter(self, param, step, amount, unit):
        param_str = param.str_for_value(param.value)
        current = float(param_str[:-2]) if '-inf' not in param_str else -70.0
        target = current + amount
        if param_str[-2:].lower() == unit:
            self.param_adjust_loop(param, step, current, target)
        elif unit == 'step':
            param.value += step * amount
        return 1

    @undo_step
    def decrease_parameter(self, param, step, amount, unit):
        amount *= -1
        param_str = param.str_for_value(param.value)
        current = float(param_str[:-2]) if '-inf' not in param_str else -70.0
        target = current + amount
        if param_str[-2:].lower() == unit:
            self.param_adjust_loop(param, step, current, target)
        elif unit == 'step':
            param.value += step * amount
        return 1

    @undo_step
    def set_parameter(self, param, step, amount, unit):
        self.unit_map[unit](param, step, amount)
        return 1

    def param_adjust_loop(self, param, step, current, target):
        while current < target:
            try:
                param.value += step  # Add the step
                current = float(param.str_for_value(param.value)[:-2])  # Update current
            except RuntimeError:
                pass
        """ The above loop will result in the new value being over by a very small amount - the below loop solves that"""
        while current > target:  # Loop while the current is greater than the target
            param.value -= step / 1000
            current = float(param.str_for_value(param.value)[:-2])
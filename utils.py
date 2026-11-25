import re
from .constants import *


def convert_int(i, slicing):
	a = int(i % 128 ** 3 / 128 ** 2)
	b = int(i % 128 ** 2 / 128)
	c = int(i % 128)
	_bytes = [c, b, a]
	return _bytes[:-1] if slicing else _bytes


def convert_bytes(bytes):
	if len(bytes) == 2:
		return (bytes[1] * 128) + bytes[0]
	elif len(bytes) == 3:
		return (bytes[2] * 16384) + (bytes[1] * 128) + bytes[0]
	# else:
	# 	return (bytes[3] * 2097152) + (bytes[2] * 16384) + (bytes[1] * 128) + bytes[0]

def create_noun_adj(nouns):
	noun_adj = []
	for i in range(0, len(nouns), 3):
		index = list(nouns[i + 2]).index(nouns[i + 1]) if nouns[i+2] else 0
		noun_adj.append(NOUNS[nouns[i]])
		noun_adj += convert_int(index + 1, True)
	return noun_adj


def sig_fig(fig):
	return len(fig) <= 6


def has_digits(input_string):
	return (any(char.isdigit() for char in input_string))


def float_to_bytes(number):
	splitted = str(number).split('.')
	integer = convert_int(int(float(splitted[0])))
	try:
		frac = convert_int(int(float(splitted[1])))
		exp = len(re.sub("[123456789]\d*", '', splitted[1]))
		if sig_fig(integer) and sig_fig(splitted[1][exp:]):
			return [exp] + integer + frac
	except IndexError:
		frac = convert_int(0)
		exp = 0
		if sig_fig(integer):
			return [exp] + integer + frac


def bytes_to_float(bytes):
	exp = bytes[0]
	integers = bytes[1:-3]
	fracs = bytes[4:]
	integer = convert_bytes(integers)
	frac = convert_bytes(fracs)
	return (
		float('{0}.{1}'.format(integer, frac))
		if exp == 1
		else float('{0}.{1}{2}'.format(integer, ('0' * (exp)), frac))
	)


def make_byte(obj, subj):
	return int(f'0x{obj}{subj}', 16)

def get_byte(quant):
	return quant >> 4, quant & 0x07

def convert_to_response_type(byte):
	return make_byte(6, byte & 0x07)


def undo_step(func):
    def wrapper(self, *args, **kwargs):
        self.song().begin_undo_step()
        try:
            result = func(self, *args, **kwargs)
        finally:
            self.song().end_undo_step()
        return result
    return wrapper


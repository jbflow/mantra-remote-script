
#SYSEX
MANUFACTURER_ID = [0, 0, 0, 0, 0]
START = [240]
END = [247]

# CONVERT_UNITS = { 'step': 0,
#                  'db': 1,
#                  'hz': 2,
#                  'ms': 3,
#                  ' %': 4}

EXTRACT_UNITS = {0: 'step',
                 1: 'db',
                 2: 'hz',
                 3: 'ms',
                 4: ' %'}

NOUNS = {'global': 0,
         'transport': 1,
         'track': 3,
         'return track': 4,
         'scene': 5,
         'cue point': 6,
         'browser': 7,
         'clip': 11,
         'clip_slot': 12,
         'device': 10,
         'volume': 18,
         'parameter': 22,
         'instrument':39,
         'audio_effect': 40,
         'midi_effect': 41,
         'browser_clip': 42,
         'favorites': 43,
         }

VERBS = {'rename': 1,
         'load': 2,
         'select': 3,
         'delete': 4,
         'duplicate': 5,
         'arm': 6,
         'unarm': 7,
         'solo': 8,
         'unsolo': 9,
         'mute': 10,
         'unmute': 11,
         'increase': 12,
         'decrease': 13,
         'set': 14,
         'move': 15,
         'undo': 17,
         'redo': 18,
         'play': 19,
         'stop': 20,
         'record': 21,
         'loop': 22,
         'launch': 23
         }














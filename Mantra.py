import Live
import queue
import json
from _Framework.ControlSurface import ControlSurface
from ableton.v3.base import nop
from .MakeConfig import MakeConfig
from .GlobalActions import GlobalActions
from .TrackActions import TrackActions
from .TransportActions import TransportActions
from .DeviceActions import DeviceActions
from .ParameterActions import ParameterActions
from .SceneActions import SceneActions
from .ClipActions import ClipActions
from .BrowserActions import BrowserActions
from .CuePointActions import CuePointActions
from .constants import *
from .Socket import Socket
from .utils import get_byte, convert_to_response_type
from .Logging import logger
import time

class Mantra(ControlSurface):
    def __init__(self, c_instance, *a, **k):
        super(Mantra, self).__init__(c_instance, *a, **k)
        self._c_instance = c_instance
        with self.component_guard():
            self.socket = Socket(c_instance, self.socket_callback)
            self.socket.start()
            self.config = MakeConfig(socket=self.socket, song=self.song())
            self._global = GlobalActions(c_instance, self.config)
            self._transport = TransportActions(c_instance)
            self._cues = CuePointActions(c_instance)
            self._track = TrackActions(c_instance)
            self._device = DeviceActions(c_instance)
            self._clip = ClipActions(c_instance)
            self._parameter = ParameterActions(c_instance)
            self._scene = SceneActions(c_instance, self.config)
            self._browser = BrowserActions(c_instance, self.config)
            self.message_queue = queue.Queue()
            
            
            
            
        self.nouns = {
            NOUNS['global']: self._global.get_action,
            NOUNS['transport']: self._transport.get_action,
            NOUNS['track']: self._track.get_action,
            NOUNS['scene']: self._scene.get_action, 
            NOUNS['cue point']: self._cues.get_action,
            NOUNS['device']: self._device.get_action,
            NOUNS['clip']: self._clip.get_action,
            NOUNS['clip_slot']: self._clip.get_action,
            NOUNS['parameter']: self._parameter.get_action,
            NOUNS['volume']: self._parameter.get_action,
            NOUNS['instrument']: self._browser.get_action,
            NOUNS['audio_effect']: self._browser.get_action,
            NOUNS['midi_effect']: self._browser.get_action,
            NOUNS['browser_clip']: self._browser.get_action,
            NOUNS['favorites']: self._browser.get_action,
        }
        
        self.check_queue = Live.Base.Timer(callback=self.process_queue, interval=20, repeat=True)
        self.check_queue.start()


    def disconnect(self):
        logger.info("Disconnecting")
        self.check_queue.stop()
        self.socket.send_message("disconnect")
        if self.socket.connection:
            self.socket.connection.close()
        self.socket.socket.close()
        super(Mantra, self).disconnect()



    def socket_callback(self, midi_bytes):
        logger.info(f'Socket callback invoked with: {midi_bytes}')
        self.message_queue.put(midi_bytes)
        

    def process_queue(self):
        if not self.message_queue.empty():
            midi_bytes = self.message_queue.get()
            self._handle_midi_bytes(midi_bytes)

            
        

    def _handle_midi_bytes(self, midi_bytes):
        
        if tuple(midi_bytes) == (240, 0, 0, 0, 0, 0, 1, 247):
            logger.info("received sysex handshake - sending response")
            self.socket.send_message(json.dumps([[240, 0, 0, 0, 0, 0, 127, 247]]))
            logger.info("scanning live set...")
            self.config.init_scan()
        elif midi_bytes[0] == 240 and midi_bytes[6] not in [0, 96]:
            self._parse_midi_bytes(midi_bytes)
        

    def _parse_midi_bytes(self, midi_bytes):
        midi_bytes = list(midi_bytes)
        midi_bytes[6] = 96
        _bytes = midi_bytes[7:-1]
        o_byte, s_byte = get_byte(_bytes[0])
        noun_adj_bytes = _bytes[1:(s_byte * 3) + 1]
        verb = _bytes[s_byte * 3 + 1]
        adverb = _bytes[s_byte * 3 + 2: -1]
        units = _bytes[-1]
        # logger.info(f'Parsed bytes - Noun Adj: {noun_adj_bytes}, Verb: {verb}, Adverb: {adverb}, Units: {units}')
        try:
            response = self.nouns[noun_adj_bytes[-3]](
                full_message=midi_bytes,
                noun_adj=noun_adj_bytes,
                verb=verb,
                adverb=adverb,
                units=units
            )
           
        except Exception as e:
            logger.error(f"Error: {e}")
            response = 0
        
        midi_bytes[len(midi_bytes) - 2] = response
        # logger.info(f'MIDI bytes before sending: {midi_bytes}')
        logger.info("MIDI_BYTES")
        logger.info(str(midi_bytes))
        self.socket.send_message(json.dumps([midi_bytes]))
        time.sleep(0.5)
        self.config.init_scan()

    

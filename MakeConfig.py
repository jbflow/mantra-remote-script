from ableton.v3.base import listens, listens_group, nop
from ableton.v3.control_surface import Component
from .constants import *
from .utils import convert_int, create_noun_adj, make_byte
import json
import time
from .Logging import logger

class MakeConfig(Component):
	def __init__(self, socket, song, *a, **k):
		super(MakeConfig, self).__init__(register_component=nop, song=song, *a, **k)
		self.socket = socket
		self.message_batch = []
		self.last_send_time = time.time()
		self._on_tracks_changed.subject = self.song
		self._on_scenes_changed.subject = self.song
		self._on_selected_track_changed.subject = self.song.view
		self._on_selected_device_changed.subject = self.song.view.selected_track.view
		self._on_track_name_changed.replace_subjects(self.song.tracks)
		self._on_scene_name_changed.replace_subjects(self.song.scenes)
		self._on_clip_name_changed.replace_subjects([clip_slot.clip for track in self.song.tracks for clip_slot in track.clip_slots if clip_slot.has_clip])
		self._on_devices_changed.replace_subjects(self.song.tracks)
		self._on_clip_slot_has_clip_changed.replace_subjects([clip_slot for track in self.song.tracks for clip_slot in track.clip_slots])
		
	def _send_batch(self):
		if self.message_batch:
			batch_message = json.dumps(self.message_batch)
			self.socket.send_message(batch_message)
			self.message_batch = []

   
	def _check_send_interval(self):
		if time.time() - self.last_send_time >= 0.01:
			self._send_batch()
			self.last_send_time = time.time()
   
	def init_scan(self):
		self.update_tracks()
		self.update_cue_points()
		self.update_return_tracks()
		self.update_scenes()
		self.update_browser()
		self.update_selected_track()
		self.update_selected_device()
		
  
	@listens("tracks")
	def _on_tracks_changed(self):
		self.update_tracks()
		self._on_track_name_changed.replace_subjects(self.song.tracks)
		self._on_devices_changed.replace_subjects(self.song.tracks)
		self._on_clip_slot_has_clip_changed.replace_subjects([clip_slot for track in self.song.tracks for clip_slot in track.clip_slots])
		
	
	@listens("scenes")
	def _on_scenes_changed(self):
		self.update_scenes()
  
	@listens("selected_track")
	def _on_selected_track_changed(self):
		self._on_selected_device_changed.subject = self.song.view.selected_track.view
		self.update_selected_track()
  
  
	@listens("selected_device")
	def _on_selected_device_changed(self):
		self.update_selected_device()
	
	@listens_group("name")
	def _on_track_name_changed(self, _):
		self.update_tracks()
	
 
	@listens_group("name")
	def _on_scene_name_changed(self, _):
		self.update_scenes()
  
	
	@listens_group("name")
	def _on_clip_name_changed(self, _):
		self.update_clips()
  
	@listens_group("devices")
	def _on_devices_changed(self, _):
		self.update_devices()
	
	@listens_group("has_clip")
	def _on_clip_slot_has_clip_changed(self, _):
		self.update_clips()

	def update_tracks(self):
		tracks = self.song.tracks
		message = {"track": [str(t.name).lower() for t in tracks]}
		self.__batch_and_log(message)
		self.update_devices()
		self.update_clips()
		self.update_selected_track()
		self.update_selected_device()
		self._check_send_interval()
		
		
  
	def update_scenes(self):
		message = {"scene": [str(s.name).lower() for s in self.song.scenes]}
		self.__batch_and_log(message)
		self._check_send_interval()
  
	def update_cue_points(self):
		message = {"cue point": [str(cue_point.name).lower() for cue_point in self.song.cue_points]}
		self.__batch_and_log(message)
		self._check_send_interval()
  
	def update_return_tracks(self):
		message = {"return track": [str(return_track.name).lower() for return_track in self.song.return_tracks]}
		self.__batch_and_log(message)
		self._check_send_interval()
		
  
	def update_clips(self):
		clips = []
		for track in self.song.tracks:
			c = []
			for clip_slot in track.clip_slots:
				c.append(str(clip_slot.clip.name).lower() if clip_slot.has_clip else "")
			clips.append(c)
		message = {"clip": clips}
		self.__batch_and_log(message)
		self._check_send_interval()
		
	def update_devices(self):
     
		devices = []
		for track in self.song.tracks:
			d = []
			for device in track.devices:
				d.append(str(device.name).lower())
			devices.append(d)
		message = {"device": devices}
		self.update_parameters()
		self.__batch_and_log(message)
		self._check_send_interval()
   
	def update_parameters(self):
		track_list = []
		for track in self.song.tracks:
			device_list = []
			for device in track.devices:
				parameter_list = []
				for parameter in device.parameters:
					parameter_list.append(parameter.name)
				else:
					if not parameter_list:
						parameter_list.append([])
				device_list.append(parameter_list)
			else:
				if not device_list:
					device_list.append([])
			track_list.append(device_list)
		message = {"parameter": track_list}
		self.__batch_and_log(message)
		self._check_send_interval()
	
 
	def update_browser(self):
		browser = self.application.browser
		message = {}
		message["favorites"] = [str(item.name).lower() for item in browser.colors[0].children]
		message["instrument"] = [str(item.name).lower() for item in browser.instruments.children]
		message["audioDevice"] = [str(item.name).lower() for item in browser.audio_effects.children]
		message["midiDevice"] = [str(item.name).lower() for item in browser.midi_effects.children]
		message["browserClip"] = [str(item.name).lower() for item in browser.clips.children]
		self.__batch_and_log(message)
		self._check_send_interval()
  
	def update_selected_track(self):
		try:
			sel_track = list(self.song.tracks).index(self.song.view.selected_track)
		except:
			sel_track = 0
		message = {"sel_track": sel_track}
		self.__batch_and_log(message)
		self._check_send_interval()
  
	def update_selected_device(self):
		if self.song.view.selected_track.view.selected_device:
			sel_device = list(self.song.view.selected_track.devices).index(self.song.view.selected_track.view.selected_device)
		else:
			sel_device = 0
		message = {"sel_device": sel_device}
		self.__batch_and_log(message)
		self._check_send_interval()
  
	def __batch_and_log(self, message):
		self.message_batch.append(message)
		# logger.info(message)
		
    


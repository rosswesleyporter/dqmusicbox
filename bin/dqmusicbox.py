#!/usr/bin/env python
#
# This code implements a simple music box.
# See https://github.com/rosswesleyporter/dqmusicbox
# It's an MP3 player on the inside.
# It looks like an old car radio on the outside (two knobs).
# It receives events from a rotary encoder for volume and invokes vlc methods in response.
# It receives events from a rotary encoder for tuning and invokes vlc to go to the next or previous tracks.
#
# Author : Ross Porter, with lots of help from the Internet, specifically including Bob Rathbone and Stephen Christopher Phillips
#          This is my first Python program...
#

import RPi.GPIO as GPIO
import time
import os
import fnmatch
import glob
import sys
import time
import vlc
import logging
import logging.handlers
 
#setup logging
#follows the example of http://blog.scphillips.com/2013/07/getting-a-python-script-to-run-in-the-background-as-a-service-on-boot/
LOG_FILENAME = "/var/log/dqmusicbox.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"
# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)
 
# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
	def __init__(self, logger, level):
		"""Needs a logger and a logger level."""
		self.logger = logger
		self.level = level
 
	def write(self, message):
		# Only log if there is a message (not just a new line)
		if message.rstrip() != "":
			self.logger.log(self.level, message.rstrip())
 
# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)
 

# Raspberry Pi Rotary Encoder Class (knobs)
# $Id: rotary_class.py,v 1.2 2014/01/31 13:34:48 bob Exp $
#
# Author : Bob Rathbone
# Site   : http://www.bobrathbone.com
#
# This class uses standard rotary encoder with push switch

class RotaryEncoder:

	CLOCKWISE=1
	ANTICLOCKWISE=2
	BUTTONDOWN=3
	BUTTONUP=4

	rotary_a = 0
	rotary_b = 0
	rotary_c = 0
	last_state = 0
	direction = 0

	# Initialise rotary encoder object
	def __init__(self,pinA,pinB,button,callback):
		self.pinA = pinA
		self.pinB = pinB
		self.button = button
		self.callback = callback

		GPIO.setmode(GPIO.BCM)
		
		# The following lines enable the internal pull-up resistors
		# on version 2 (latest) boards
		GPIO.setwarnings(False)
		GPIO.setup(self.pinA, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.pinB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		# Add event detection to the GPIO inputs
		GPIO.add_event_detect(self.pinA, GPIO.FALLING, callback=self.switch_event)
		GPIO.add_event_detect(self.pinB, GPIO.FALLING, callback=self.switch_event)
		GPIO.add_event_detect(self.button, GPIO.BOTH, callback=self.button_event, bouncetime=200)
		return

	# Call back routine called by switch events
	def switch_event(self,switch):
		if GPIO.input(self.pinA):
			self.rotary_a = 1
		else:
			self.rotary_a = 0

		if GPIO.input(self.pinB):
			self.rotary_b = 1
		else:
			self.rotary_b = 0

		self.rotary_c = self.rotary_a ^ self.rotary_b
		new_state = self.rotary_a * 4 + self.rotary_b * 2 + self.rotary_c * 1
		delta = (new_state - self.last_state) % 4
		self.last_state = new_state
		event = 0

		if delta == 1:
			if self.direction == self.CLOCKWISE:
				# print "Clockwise"
				event = self.direction
			else:
				self.direction = self.CLOCKWISE
		elif delta == 3:
			if self.direction == self.ANTICLOCKWISE:
				# print "Anticlockwise"
				event = self.direction
			else:
				self.direction = self.ANTICLOCKWISE
		if event > 0:
			self.callback(event)
		return


	# Push button up event
	def button_event(self,button):
		if GPIO.input(button): 
			event = self.BUTTONUP 
		else:
			event = self.BUTTONDOWN 
		self.callback(event)
		return

	# Get a switch state
	def getSwitchState(self, switch):
		return  GPIO.input(switch)

# End of RotaryEncoder class


#Setup the media player with a playlist of all music in a specific folder
music_path = '/home/pi/dqmusicbox/music'
music_files = [os.path.join(dirpath, f)
               for dirpath, dirnames, files, in sorted(os.walk(music_path))
               for extension in ['mp3', 'flac']
               for f in fnmatch.filter(files, '*.' + extension)]
player = vlc.MediaPlayer()
medialist = vlc.MediaList(music_files)
mlplayer = vlc.MediaListPlayer()
mlplayer.set_media_player(player)
mlplayer.set_media_list(medialist)

#Setup the tuning knob (rotary encoder)
TUNING_NEXT = 3 	        # Pin 5 
TUNING_PREVIOUS = 4	        # Pin 7
TUNING_PRESS = 2	        # Pin 3
button_down_time = 0
last_knob_event = time.time()

def tuning_event(event):
        global tuning_knob
        global button_down_time
        global last_knob_event
        last_knob_event = time.time()
        #logger.info('tuning event = ' + str(event))
        
        if event == RotaryEncoder.CLOCKWISE:
                logger.info('tuning CLOCKWISE')
                mlplayer.next()
                logger.info('track = ' + str(player.get_media().get_mrl()))
                return
        
        if event == RotaryEncoder.ANTICLOCKWISE:
                logger.info('tuning ANTICLOCKWISE')
                mlplayer.previous()
                logger.info('track = ' + str(player.get_media().get_mrl()))
                return

        if event == RotaryEncoder.BUTTONDOWN:
                logger.info('tuning BUTTONDOWN')
                button_down_time = time.time()
                mlplayer.pause()
                return

        if event == RotaryEncoder.BUTTONUP:
                logger.info('tuning BUTTONUP')
                #a 10 second press is a shutdown request
                if time.time() > button_down_time + 10 and time.time() < button_down_time + 30:
                        logger.info('tuning 10 second press; initiating shutdown -h now')
                        mlplayer.stop()
                        os.system("sudo shutdown -h now")
                return
        return


tuning_knob = RotaryEncoder(TUNING_NEXT, TUNING_PREVIOUS, TUNING_PRESS, tuning_event)


#Set the system and VLC volume levels.
#This program does not otherwise change the system volume level
#The volume knob will be used to set the VLC volume level
os.system('sudo amixer sset Headphone 100%')
player.audio_set_volume(30)


#Setup the volume knob
VOLUME_UP = 9 
VOLUME_DOWN = 11
VOLUME_PRESS = 10

def volume_event(event):
        global volume_knob
        global button_down_time
        global last_knob_event
        last_knob_event = time.time()
        #logger.info('volume event = ' + str(event))

        if event == RotaryEncoder.CLOCKWISE:
                logger.info('volume CLOCKWISE')
                if mlplayer.is_playing() == False:
                        logger.info('play')
                        mlplayer.play()
                        logger.info('track = ' + str(player.get_media().get_mrl()))
                if player.audio_get_volume() <= 95:
                        player.audio_set_volume(player.audio_get_volume()+5)
                        logger.info('volume increased to ' + str(player.audio_get_volume()))
                return
        
        if event == RotaryEncoder.ANTICLOCKWISE:
                logger.info('volume ANTICLOCKWISE')
                if player.audio_get_volume() >= 5:
                        player.audio_set_volume(player.audio_get_volume()-5)
                        logger.info('volume decreased to ' + str(player.audio_get_volume()))
                return
        
        if event == RotaryEncoder.BUTTONDOWN:
                logger.info('volume BUTTONDOWN')
                button_down_time = time.time()
                mlplayer.pause()
                return
        
        if event == RotaryEncoder.BUTTONUP:
                logger.info('volume BUTTONUP')
                if time.time() > button_down_time + 10 and time.time() < button_down_time + 30:
                        logger.info('volume 10 second press; initiating shutdown -h now')
                        mlplayer.stop()
                        os.system("sudo shutdown -h now")
                return
        
        return

volume_knob = RotaryEncoder(VOLUME_UP, VOLUME_DOWN, VOLUME_PRESS, volume_event)


#turn on indicator light to show that the music box is ready
INDICATOR_LIGHT = 22
GPIO.setmode(GPIO.BCM)
GPIO.setup(INDICATOR_LIGHT, GPIO.OUT)
GPIO.output(INDICATOR_LIGHT, True)


while True:
        time.sleep(10)
        if (last_knob_event + 3600) < time.time() and mlplayer.is_playing() == True:  #stop music if no knob activity in the last hour
                logger.info('automatic timeout')
                mlplayer.pause()

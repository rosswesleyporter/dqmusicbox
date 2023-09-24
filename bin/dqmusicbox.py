#!/usr/bin/env python
#
'''
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
######################################################
# See http://DementiaMusicPlayer.org, https://github.com/rosswesleyporter/dqmusicbox
# This code implements a simple retro-style two-knob music player.
# The code is intended to run as a service at boot.
# 95% of the code does setup/config and runs in about a second.
# Most of this setup is getting things ready for VLC (vlc-nox) which does the actual audio playback.
# The remaining 5% of code handles knob events, some of which are handed off to VLC.
# The order of execution is pretty much top-to-bottom, so it's an easy read top-to-bottom.
# Key actions:
#   - Creates a Python list of all the music on the USB drive, then creates a VLC playlist.
#   - Configures the hardware audio device & creates a VLC media player instance. 
#   - Receives events from a rotary encoder for volume and invokes VLC methods in response.
#   - Receives events from a rotary encoder for songs and invokes vlc to go to the next or previous tracks.
#
# Author : Ross Porter, with lots of help from the Internet, specifically
#          including Bob Rathbone and Stephen C Phillips.
'''

# Import modules that are included with DietPi
import RPi.GPIO as GPIO
import sys
import time
import os
import fnmatch
import glob
import sys
import time
import logging
import logging.handlers
import subprocess
 
# SETUP LOGGING
# Examples/docs that I followed for log config
# http://blog.scphillips.com/2013/07/getting-a-python-script-to-run-in-the-background-as-a-service-on-boot/
# https://docs.python.org/3/library/logging.html
# https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/
logger = logging.getLogger('dqmusicbox') #This will usually be /var/log/dqmusicbox.log
logger.setLevel(logging.INFO)
handler = logging.handlers.TimedRotatingFileHandler("/var/log/dqmusicbox.log", when="midnight", backupCount=2)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# stdout and stderr should also go to log file
class StdLogger(object):
	def __init__(self, logger, log_level):
		"""Log stdout and stderr to log file"""
		self.logger = logger
		self.level = log_level
 
	def write(self, message):
                self.logger.log(self.level, message.rstrip())
 
sys.stdout = StdLogger(logger, logging.INFO)
sys.stderr = StdLogger(logger, logging.ERROR)

# OK, let's get this party started.
# Log that we're starting up
logger.info("dqmusicbox starting.")

# Now we have enough things in place that we can define what to do if this program has to exit.
def cleanup():
        logger.info('In cleanup(). Exiting shortly.')
        GPIO.cleanup()
        return

# Import the modules that are not included with DietPi, so do exception handling.
# First, import the Python bindings for the VLC API
try:
    import vlc
except:
        logger.error("Import vlc module failed -- please insure that the vlc module is installed. Exiting.")
        cleanup()
        sys.exit(1)
else:
    logger.info("vlc module successfully imported.")

# Import Bob Rathbone's module for rotary encoder event handling.
try:
    from rotary_class import *
except:
        logger.error("Import rotary_class module failed -- please insure that the rotary_class module is available. Exiting.")
        cleanup()
        sys.exit(1)
else:
    logger.info("rotary_class module successfully imported.")

	
# Define a few things about GPIO / pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False);
SONGS_NEXT = 3
SONGS_PREVIOUS = 4
SONGS_PRESS = 2
VOLUME_UP = 9 
VOLUME_DOWN = 11
VOLUME_PRESS = 10
INDICATOR_LIGHT = 27

# Build a list of all music on the USB drive /mnt/usb1
# Music can be MP3, FLAC, iTunes/AAC, Ogg Vorbis; must have a proper file extension i.e. .mp3, .flac, .m4a, .ogg
# Gives the USB drive with music up to 60 seconds to automount and be available
music_path = '/media/usb1'
for x in range(60):
	if x == 59:
		msg =  'Fail. Exiting as no music files found in {}'.format(music_path)		
		logger.error(msg)
		cleanup()
		exit(1)
	music_files = [os.path.join(dirpath, f)
		for dirpath, dirnames, files, in sorted(os.walk(music_path))
		for extension in ['mp3', 'flac', 'm4a', 'ogg']
		for f in fnmatch.filter(sorted(files), '*.' + extension)]
	if len(music_files) == 0:
		logger.info('No music files found yet. Pausing for one second')
		time.sleep(1)
	else:
		msg = 'Success! Number of music files found: {}'.format(len(music_files))
		logger.info(msg)
		break

try:
        player = vlc.MediaPlayer()
except:
        logger.error("Unable to create vlc.MediaPlayer() object. Exiting.")
        cleanup()
        sys.exit(1)
else:
        logger.info("vlc.MediaPlayer() object created.")

try:
        medialist = vlc.MediaList(music_files)
except:
        logger.error("Unable to create vlc.MediaList(music_files) object. Exiting.")
        cleanup()
        sys.exit(1)
else:
        logger.info("vlc.MediaList(music_files) created.")
        
try:
        mlplayer = vlc.MediaListPlayer()
except:
        logger.error("Unable to create vlc.MediaListPlayer() oboject. Exiting.")
        cleanup()
        sys.exit(1)
else:
        logger.info("vlc.MediaListPlayer() created.")

# Get VLC going - createa media player instance and turn the Python list into a VLC playlist        
mlplayer.set_media_player(player)
mlplayer.set_media_list(medialist)

# Setup the songs knob (rotary encoder)
button_down_time = 0
last_knob_event = time.time()

# Event handler for the songs knob
def songs_event(event):
        global button_down_time
        global last_knob_event
        last_knob_event = time.time()
        
        # Handle knob request for next song
        if event == RotaryEncoder.CLOCKWISE:
                logger.info('songs CLOCKWISE')
                mlplayer.next()
                logger.info('track = ' + str(player.get_media().get_mrl()))
                return
        
        # Handle knob request for previous song
        if event == RotaryEncoder.ANTICLOCKWISE:
                logger.info('songs ANTICLOCKWISE')
                mlplayer.previous()
                logger.info('track = ' + str(player.get_media().get_mrl()))
                return

        # Handle knob request for pause
        if event == RotaryEncoder.BUTTONDOWN:
                logger.info('songs BUTTONDOWN')
                button_down_time = time.time()
                mlplayer.pause()
                return

        # Handle knob request (long hold) for system reboot
        if event == RotaryEncoder.BUTTONUP:
                logger.info('songs BUTTONUP')
                # A 10 second press is a shutdown request
                if time.time() > button_down_time + 10 and time.time() < button_down_time + 30:
                        logger.info('songs 10 second press; rebooting now')
                        mlplayer.stop()
                        os.system("sudo reboot")
                return

        logger.error('Something weird happened. Unhandled songs knob event?')
        
        return


try:
        songs_knob = RotaryEncoder(SONGS_NEXT, SONGS_PREVIOUS, SONGS_PRESS, songs_event)
except:
        logger.error("Unable to create songs_knob object. Exiting.")
        cleanup()
        sys.exit(1)
else:
        logger.info("Created songs_knob object.")



# Set the system volume level.
# There are two volume levels - system, vlc.
# Setting the system volume level is device specific,
# i.e. the command line for the built-in headphone jack is different from a USB DAC.
# Ideally this code would do audio device detection.
# But I'll go with the simple and sufficient approach of running multiple commands thus supporting multiple devices.

# Set volume level for Pi's built-on headphone jack
try:
	os.system('sudo amixer -c 0 sset PCM 100%')
except:
	logger.error("WARNING: Failed when setting the system volume level for the built-in headphone jack (but this may not be your audio device): amixer -c 0 sset PCM 100%")
else:
	 logger.info("Set system volume level for the built-in headphone jack: amixer -c 0 sset PCM 100%")

# Set the system volume level for StarTech/Syba USB audio DAC
try:
	os.system("sudo amixer sset 'IEC958 In' 100%")
except:
	logger.error("WARNING: Failed when setting the system volume level for the StarTech/Syba USB audio DAC (but this may not be your audio device): amixer -c 0 sset PCM 100%")
else:
	 logger.info("Set system volume level for the StarTech/Syba USB audio DAC: amixer -c 0 sset PCM 100%")

# Set volume level for the Adafruit white dongle USB audio adapter         
try:
        os.system('sudo amixer sset Headphone 100%')
except:
        logger.error("WARNING: Failed when setting the system volume level for the Adafruit white dongle USB audio adapter (but this may not be your audio device): sudo amixer sset Headphone 100%")
else:
        logger.info("Set system volume level for the Adafruit white dongle USB audio adapter: amixer sset Headphone 100%'")


# Set volume level for Pluggable USB audio adapter
try:
        os.system('sudo amixer sset Speaker 100%')
except:
        logger.error("WARNING: Failed when setting the system volume level for the Pluggable USB audio adapter (but this may not be your audio device): sudo amixer sset Speaker 100%")
else:
        logger.info("Set system volume level for the Pluggable USB audio adapter: sudo amixer sset Speaker 100%")


# Log a bit of diagnostic info about audio
proc = subprocess.Popen(['sudo amixer -c 0'], stdout=subprocess.PIPE, shell=True)
(out,err) = proc.communicate()
logger.info('A bit of diagnostic info on the state of the Pi built-in headphone jack')
logger.info(out)

# Set the initial vlc volume level.
try:
        player.audio_set_volume(60)
except:
        logger.error("Failed to set initial vlc volume level.")
else:
        logger.info("Set initial vlc volume level.")


# Setup the volume knob
# Event handler for the volume knob
def volume_event(event):
        global button_down_time
        global last_knob_event
        last_knob_event = time.time()
        increment = 2

        #handle knob volume up request
        if event == RotaryEncoder.CLOCKWISE:
                logger.info('volume CLOCKWISE')
                if mlplayer.is_playing() == False:
                        logger.info('play')
                        mlplayer.play()
                        logger.info('track = ' + str(player.get_media().get_mrl()))
                if player.audio_get_volume() < 150: #yes, 150% is the max - uses vlc's volume boost capability to compensate for the Pi's somewhat quiet headphone jack
                        player.audio_set_volume(player.audio_get_volume()+increment)
                        logger.info('volume increased to ' + str(player.audio_get_volume()))
                return
        
        #handle knob volume down request
        if event == RotaryEncoder.ANTICLOCKWISE:
                logger.info('volume ANTICLOCKWISE')
                #emulate old radios such that turning the volume to zero means turning the device off (we'll pause)
                if player.audio_get_volume() > 0 and player.audio_get_volume() <= increment:
                        player.audio_set_volume(0)
                        mlplayer.pause()
                        logger.info('volume decreased to 0, so pausing')
                #decrease volume, but don't go below zero
                elif player.audio_get_volume() >= increment:
                        player.audio_set_volume(player.audio_get_volume()-increment)
                        logger.info('volume decreased to ' + str(player.audio_get_volume()))
                return
        
        #handle knob (tap) pause request
        if event == RotaryEncoder.BUTTONDOWN:
                logger.info('volume BUTTONDOWN')
                button_down_time = time.time()
                mlplayer.pause()
                return
        
        #handle knob long hold (10-30 sec) request for system shutdown
        if event == RotaryEncoder.BUTTONUP:
                logger.info('volume BUTTONUP')
                if time.time() > button_down_time + 10 and time.time() < button_down_time + 30:
                        logger.info('songs 10 second press; initiating shutdown -h now')
                        mlplayer.stop()
                        os.system("sudo shutdown -h now")
                return
        
        logger.error('Something weird happened. Unhandled volume knob event?')
        
        return

try:
        volume_knob = RotaryEncoder(VOLUME_UP, VOLUME_DOWN, VOLUME_PRESS, volume_event)
except:
        logger.error('Unable to create volume_knob object. Exiting')
        cleanup()
        sys.exit(1)
else:
        logger.info('volume_knob object created')


# Turn on indicator light to show that the music box is ready
GPIO.setup(INDICATOR_LIGHT, GPIO.OUT)
GPIO.output(INDICATOR_LIGHT, True)
logger.info('Green light turned on - music should start playing momentarily')

# Start some music playing
mlplayer.play()

while True:
        time.sleep(600)
        if (last_knob_event + 86400) < time.time() and mlplayer.is_playing() == True:  #pause music if no knob activity in the last 24 hours
                logger.info('automatic timeout')
                mlplayer.pause()

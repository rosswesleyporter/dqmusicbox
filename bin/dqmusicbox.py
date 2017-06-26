#!/usr/bin/env python
#
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
# This code implements a simple music box.
# It's an MP3 player on the inside.
# It looks like an old car radio on the outside (two knobs).
# It creates a vlc playlist of all the music on the Pi.
# It receives events from a rotary encoder for volume and invokes vlc methods in response.
# It receives events from a rotary encoder for songs and invokes vlc to go to the next or previous tracks.
#
# Author : Ross Porter, with lots of help from the Internet, specifically
#          including Bob Rathbone and Stephen C Phillips.
#          This is my first Python program...

# Import modules that are included with Rapsbian
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
 
#SETUP LOGGING
#Some of this log setup is not necessary given DietPi's RAM logging, but useful if this code ever runs on regular Raspbian
#Here are the examples and documentaton that I followed
#http://blog.scphillips.com/2013/07/getting-a-python-script-to-run-in-the-background-as-a-service-on-boot/
#https://docs.python.org/3/library/logging.html
#https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/
#https://www.loggly.com/ultimate-guide/python-logging-basics/
#https://docs.python.org/3/library/logging.handlers.html#logging.handlers.TimedRotatingFileHandler
#https://docs.python.org/3.1/library/logging.html
logger = logging.getLogger('dqmusicbox')
logger.setLevel(logging.INFO)
handler = logging.handlers.TimedRotatingFileHandler("/var/log/dqmusicbox.log", when="midnight", backupCount=2)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
#stdout and stderr should also go to log file
class StdLogger(object):
	def __init__(self, logger, log_level):
		"""Log stdout and stderr to log file"""
		self.logger = logger
		self.level = log_level
 
	def write(self, message):
                self.logger.log(self.level, message.rstrip())
 
sys.stdout = StdLogger(logger, logging.INFO)
sys.stderr = StdLogger(logger, logging.ERROR)

#OK, let's get this party started.
#Log that we're starting up
logger.info("dqmusicbox starting.")

#Define a few things about GPIO / pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False);
SONGS_NEXT = 3
SONGS_PREVIOUS = 4
SONGS_PRESS = 2
VOLUME_UP = 9 
VOLUME_DOWN = 11
VOLUME_PRESS = 10
INDICATOR_LIGHT = 27

#Now we have enough things in place that we can define what to do if this program has to exit.
def cleanup():
        logger.info('In cleanup(). Exiting shortly.')
        GPIO.cleanup()
        return

#Import the module that with Python bindings for vlc.
#This is not included with Raspbian.
#Didn't import this above, as we want to handle the exception
try:
    import vlc
except:
        logger.error("Import vlc module failed -- please insure that the vlc module is installed. Exiting.")
        cleanup()
        sys.exit(1)
else:
    logger.info("vlc module successfully imported.")

#Import Bob Rathbone's module for rotary encoder event handling.
try:
    from rotary_class import *
except:
        logger.error("Import rotary_class module failed -- please insure that the rotary_class module is available. Exiting.")
        cleanup()
        sys.exit(1)
else:
    logger.info("rotary_class module successfully imported.")


#Building a Python list of all music on a USB thumb drive automounted by DietPi to /mnt/usb_1
#Music can be MP3, FLAC, iTunes/AAC, Ogg Vorbis; must have a proper file extension i.e. .mp3, .flac, .m4a, .ogg
#Then engage the media player to build a playlist based on this Python list
music_path = '/mnt/usb_1'
music_files = [os.path.join(dirpath, f)
               for dirpath, dirnames, files, in sorted(os.walk(music_path))
               for extension in ['mp3', 'flac', 'm4a', 'ogg']
               for f in fnmatch.filter(sorted(files), '*.' + extension)]
if len(music_files) == 0:
        msg = 'No music files found in {}. {}'.format(len(music_files),'Exiting.')
        logger.error(msg)
        cleanup()
        exit(1)
else:
        msg = 'Number of music files found: {}'.format(len(music_files))
        logger.info(msg)

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
        
mlplayer.set_media_player(player)
mlplayer.set_media_list(medialist)

#Setup the songs knob (rotary encoder)
button_down_time = 0
last_knob_event = time.time()

#event handler for the songs knob
def songs_event(event):
        global button_down_time
        global last_knob_event
        last_knob_event = time.time()
        
	#handle knob request for next song
        if event == RotaryEncoder.CLOCKWISE:
                logger.info('songs CLOCKWISE')
                mlplayer.next()
                logger.info('track = ' + str(player.get_media().get_mrl()))
                return
        
	#handle knob request for previous song
        if event == RotaryEncoder.ANTICLOCKWISE:
                logger.info('songs ANTICLOCKWISE')
                mlplayer.previous()
                logger.info('track = ' + str(player.get_media().get_mrl()))
                return

	#handle knob request for pause
        if event == RotaryEncoder.BUTTONDOWN:
                logger.info('songs BUTTONDOWN')
                button_down_time = time.time()
                mlplayer.pause()
                return

	#handle knob request (long hold) for system reboot
        if event == RotaryEncoder.BUTTONUP:
                logger.info('songs BUTTONUP')
                #a 10 second press is a shutdown request
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


#Set the system volume level. This program does not otherwise change the system volume level.
#This is somewhat specific to the audio device.
#It should work for the Pi's built-in headphone jack.

#set volume level for Pi's built-on headphone jack
try:
	os.system('sudo amixer -c 0 sset PCM 100%')
except:
	logger.error("The following command failed: amixer -c 0 sset PCM 100%")
else:
	 logger.info("Set system volume level with amixer -c 0 sset PCM 100%")

#set volume level for the Adafruit white dongle USB audio adapter         
#try:
#        os.system('sudo amixer sset Headphone 100%')
#except:
#        logger.error("The following command failed: sudo amixer sset Headphone 100%. Try this from the command line. You may need to change your system audio configuration. Easiest if you use the recommended USB audio adapter.")
#else:
#        logger.info("Set system volume level with sudo amixer sset Headphone 100%'")


#set volume level for Pluggable USB audio adapter
#try:
#        os.system('sudo amixer sset Speaker 100%')
#except:
#        logger.error("The following command failed: sudo amixer sset Speaker 100%. Try this from the command line. You may need to change your system audio configuration. Easiest if you use the recommended USB audio adapter.")
#else:
#        logger.info("Set system volume level")


#log a bit of diagnostic info about audio
proc = subprocess.Popen(['sudo amixer -c 0'], stdout=subprocess.PIPE, shell=True)
(out,err) = proc.communicate()
logger.info('A bit of diagnostic info on the state of the Pi built-in headphone jack')
logger.info(out)

#Set the initial vlc volume level.
try:
        player.audio_set_volume(30)
except:
        logger.error("Failed to set initial vlc volume level.")
else:
        logger.info("Set initial vlc volume level.")


#Setup the volume knob
#event handler for the volume knob
def volume_event(event):
        global button_down_time
        global last_knob_event
        last_knob_event = time.time()

	#handle knob volume up request
        if event == RotaryEncoder.CLOCKWISE:
                logger.info('volume CLOCKWISE')
                if mlplayer.is_playing() == False:
                        logger.info('play')
                        mlplayer.play()
                        logger.info('track = ' + str(player.get_media().get_mrl()))
                if player.audio_get_volume() <= 145: #yes, this is 145% - uses vlc's volume boost capability to compensate for the Pi's somewhat quiet headphone jack
                        player.audio_set_volume(player.audio_get_volume()+5)
                        logger.info('volume increased to ' + str(player.audio_get_volume()))
                return
        
	#handle knob volume down request
        if event == RotaryEncoder.ANTICLOCKWISE:
                logger.info('volume ANTICLOCKWISE')
                if player.audio_get_volume() >= 5:
                        player.audio_set_volume(player.audio_get_volume()-5)
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


#turn on indicator light to show that the music box is ready
GPIO.setup(INDICATOR_LIGHT, GPIO.OUT)
GPIO.output(INDICATOR_LIGHT, True)


while True:
        time.sleep(600)
        if (last_knob_event + 3600) < time.time() and mlplayer.is_playing() == True:  #stop music if no knob activity in the last hour
                logger.info('automatic timeout')
                mlplayer.pause()

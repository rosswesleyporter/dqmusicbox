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
# Purpose: This class handles rotary encoders (knobs).
# Author : Bob Rathbone
# Source : http://www.bobrathbone.com/raspberrypi/Raspberry%20Rotary%20Encoders.pdf
# The above includes the code and is an excellent article on how rotary encoders operate.
######################################################

import RPi.GPIO as GPIO

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
		
		# The following lines enable the internal pull-up resistors
		# on version 2 boards
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

# End of RotaryEcnode class

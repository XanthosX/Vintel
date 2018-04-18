###########################################################################
#  Vintel - Visual Intel Chat Analyzer									  #
#  Copyright (C) 2014-15 Sebastian Meyer (sparrow.242.de+eve@gmail.com )  #
#																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTYf without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#																		  #
#																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import os
import subprocess
import sys
import re
import requests
import time
import six
import logging 
import pyttsx3
from win32com.server.util import wrap

from collections import namedtuple
from PyQt5.QtCore import QThread
from pkg_resources import resource_filename 
from six.moves import queue

import logging
from vi.singleton import Singleton

global gPygletAvailable


try:
    import pyglet
    from pyglet import media

    gPygletAvailable = True
except ImportError:
    gPygletAvailable = False


class SoundManager(six.with_metaclass(Singleton)):
    SOUNDS = {"alarm": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "kos": "178031__zimbot__transporterstartbeep0-sttos-recreated.wav",
              "request": "178028__zimbot__bosun-whistle-sttos-recreated.wav"}

    soundVolume = 25  # Must be an integer between 0 and 100
    soundActive = False
    soundAvailable = False
    useDarwinSound = False
    useSpokenNotifications = True
    _soundThread = None

    def __init__(self):
        self._soundThread = self.SoundThread()
        self.soundAvailable = self.platformSupportsAudio()
        if not self.platformSupportsSpeech():
            self.useSpokenNotifications = False
        if self.soundAvailable:
            self._soundThread.start()

    def platformSupportsAudio(self):
        return self.platformSupportsSpeech() or gPygletAvailable

    def platformSupportsSpeech(self):
        if self._soundThread.isDarwin or self._soundThread.usePyTTS:
            return True
        return True

    def setUseSpokenNotifications(self, newValue):
        if newValue is not None:
            self.useSpokenNotifications = newValue

    def setSoundVolume(self, newValue):
        """ Accepts and stores a number between 0 and 100.
        """
        self.soundVolume = max(0, min(100, newValue))
        self._soundThread.setVolume(self.soundVolume)

    def playSound(self, name="alarm", message="Incoming enemies", abbreviatedMessage="red alert"):
        """ Schedules the work, which is picked up by SoundThread.run()
        """
        if name is False:
            name = "alarm"
            message = "this is a test"
            abbreviatedMessage = "test"
        if self.soundAvailable and self.soundActive:
            if self.useSpokenNotifications:
                audioFile = None
            else:
                audioFile = resource_filename(__name__,"ui/res/{0}".format(self.SOUNDS[name]))
            self._soundThread.queue.put((audioFile, message, abbreviatedMessage))

    def quit(self):
        if self.soundAvailable:
            self._soundThread.quit()

    #
    #  Inner class handle audio playback without blocking the UI
    #

    class SoundThread(QThread): 
        usePyTTS = True 
        queue = None
        isDarwin = sys.platform.startswith("darwin")
        volume = 25


        def __init__(self):
            QThread.__init__(self)
            self.queue = queue.Queue()
            if gPygletAvailable:
                self.player = media.Player()
            else:
                self.player = None	
            if self.usePyTTS:
                self.speech_engine = pyttsx3.init()
            self.active = True
            


        def setVolume(self, volume):
            self.volume = volume


        def run(self):
            while True:
                audioFile, message, abbreviatedMessage = self.queue.get()
                if not self.active:
                    return
                if SoundManager().useSpokenNotifications and (message != "" or abbreviatedMessage != ""):
                    if abbreviatedMessage != "":
                        message = abbreviatedMessage
                    if not self.speak(message):
                        self.playAudioFile(audioFile, False)
                        logging.error("SoundThread: sorry, speech not yet implemented on this platform")
                elif audioFile is not None:
                    self.playAudioFile(audioFile, False)

        def quit(self):
            self.active = False
            self.queue.put((None, None, None))
            if self.player:
                self.player.pause()
                self.player.delete()
            QThread.quit(self)


        def speak(self, message):
            if self.usePyTTS:
                self.speech_engine.say(message)  # experimental
                self.speech_engine.setProperty('volume',self.volume/100.0)
                self.speech_engine.setProperty('rate',130)
                self.speech_engine.runAndWait()
            elif self.isDarwin:
                self.darwinSpeak(message)
            else:
                return False
            return True


        def handleIdleTasks(self):
            self.speakRandomChuckNorrisJoke()


        # Audio subsytem access

        def playAudioFile(self, filename, stream=False):
            try:
                volume = float(self.volume) / 100.0
                if self.player:
                    src = media.load(filename, streaming=stream)
                    self.player.queue(src)
                    self.player.volume = volume
                    self.player.play()
                elif self.isDarwin:
                    subprocess.call(["afplay -v {0} {1}".format(volume, filename)], shell=True)
            except Exception as e:
                logging.error("SoundThread.playAudioFile exception: %s", e)

        def darwinSpeak(self, message):
            try:
                os.system("say [[volm {0}]] '{1}'".format(float(self.volume) / 100.0, message))
            except Exception as e:
                logging.error("SoundThread.darwinSpeak exception: %s", e)

        def splitText(self, inputText, maxLength=100):
            """
            Try to split between sentences to avoid interruptions mid-sentence.
            Failing that, split between words.
            See splitText_rec
            """

            def splitTextRecursive(inputText, regexps, maxLength=maxLength):
                """
                Split a string into substrings which are at most maxLength.
                Tries to make each substring as big as possible without exceeding
                maxLength.
                Will use the first regexp in regexps to split the input into
                substrings.
                If it it impossible to make all the segments less or equal than
                maxLength with a regexp then the next regexp in regexps will be used
                to split those into subsegments.
                If there are still substrings who are too big after all regexps have
                been used then the substrings, those will be split at maxLength.

                Args:
                    inputText: The text to split.
                    regexps: A list of regexps.
                        If you want the separator to be included in the substrings you
                        can add parenthesis around the regular expression to create a
                        group. Eg.: '[ab]' -> '([ab])'

                Returns:
                    a list of strings of maximum maxLength length.
                """
                if (len(inputText) <= maxLength):
                    return [inputText]

                # Mistakenly passed a string instead of a list
                if isinstance(regexps, basestring):
                    regexps = [regexps]
                regexp = regexps.pop(0) if regexps else '(.{%d})' % maxLength

                textList = re.split(regexp, inputText)
                combinedText = []
                # First segment could be >max_length
                combinedText.extend(splitTextRecursive(textList.pop(0), regexps, maxLength))
                for val in textList:
                    current = combinedText.pop()
                    concat = current + val
                    if (len(concat) <= maxLength):
                        combinedText.append(concat)
                    else:
                        combinedText.append(current)
                        # val could be > maxLength
                        combinedText.extend(splitTextRecursive(val, regexps, maxLength))
                return combinedText

            return splitTextRecursive(inputText.replace('\n', ''), ['([\,|\.|;]+)', '( )'])

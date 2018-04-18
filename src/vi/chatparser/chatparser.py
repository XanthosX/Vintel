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
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#																		  #
#																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import datetime
import os
import time
import six
import logging 

if six.PY2:
    from io import open

from bs4 import BeautifulSoup
from vi import states
from PyQt5.QtWidgets import QMessageBox


from .parser_functions import parseStatus
from .parser_functions import parseUrls, parseShips, parseSystems

# Names the local chatlogs could start with (depends on l10n of the client)
LOCAL_NAMES = ("Local", "Lokal", six.text_type("\u041B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439"))


class ChatParser(object):
    """ ChatParser will analyze every new line that was found inside the Chatlogs.
    """

    def __init__(self, path, rooms, systems, logging):
        """ path = the path with the logs
            rooms = the rooms to parse"""
        self.path = path  # the path with the chatlog
        self.rooms = rooms  # the rooms to watch (excl. local)
        self.systems = systems  # the known systems as dict name: system
        self.fileData = {}  # informations about the files in the directory
        self.knownMessages = []  # message we allready analyzed
        self.locations = {}  # informations about the location of a char
        self.ignoredPaths = []
        self.logging = logging
        self._collectInitFileData(path)

    def _collectInitFileData(self, path):
        currentTime = time.time()
        maxDiff = 60 * 60 * 24  # what is 1 day in seconds
        for filename in os.listdir(path):
            fullPath = os.path.join(path, filename)
            fileTime = os.path.getmtime(fullPath)
            encoding = 'utf-16-le'
            if len(filename)<20:
                encoding = 'utf-8'
            if currentTime - fileTime < maxDiff:
                self.addFile(fullPath,encoding)

    def addFile(self, path, encod):
        lines = None
        content = ""
        filename = os.path.basename(path)
        roomname = filename[:-20]
        try:
            with open(path, "r", encoding=encod, errors='ignore') as f:
                content = f.read()
        except Exception as e:
            self.ignoredPaths.append(path)
            QMessageBox.warning(None, "Read a log file failed!", "File: {0} - problem: {1}".format(path, six.text_type(e)), QMessageBox.Ok)
            return None
        charname = None
        try:
            charname = self.fileData[path]["charname"]
        except:
            pass
        lines = content.split("\n")
        if path not in self.fileData or "charname" not in self.fileData.get(path, []):
            self.fileData[path] = {}
            sessionStart = None
            # for local-chats we need more infos
            for line in lines:
                if "listener:" in line.lower():
                    charname = line[line.find(":") + 1:].strip()
                elif "session started:" in line.lower():
                    sessionStr = line[line.find(":") + 1:].strip()
                    sessionStart = datetime.datetime.strptime(sessionStr, "%Y.%m.%d %H:%M:%S")
                if charname and sessionStart:
                    self.fileData[path]["charname"] = charname
                    self.fileData[path]["sessionstart"] = sessionStart
                    break
        self.fileData[path]["lines"] = len(lines)
        return lines

    def _lineToMessage(self, line, roomname):
        # finding the timestamp
        line = line.decode('utf-8')
        timeStart = line.find("[") + 1
        timeEnds = line.find("]")
        timeStr = line[timeStart:timeEnds].strip()
        try:
            timestamp = datetime.datetime.strptime(timeStr, "%Y.%m.%d %H:%M:%S")
        except ValueError as e:
            logging.critical(e)
            return None
        # finding the username of the poster
        userEnds = line.find(">")
        username = line[timeEnds + 1:userEnds].strip()
        # finding the pure message
        text = line[userEnds + 1:].strip()  # text will the text to work an
        originalText = text
        formatedText = u"<rtext>{0}</rtext>".format(text)
        soup = BeautifulSoup(formatedText, 'html.parser')
        rtext = soup.select("rtext")[0]
        systems = set()
        upperText = text.upper()

        # KOS request
        if upperText.startswith("XXX "):
            return Message(roomname, text, timestamp, username, systems, upperText, status=states.KOS_STATUS_REQUEST)
        elif roomname.startswith("="):
            return Message(roomname, "xxx " + text, timestamp, username, systems, "XXX " + upperText, status=states.KOS_STATUS_REQUEST)
        elif upperText.startswith("VINTELSOUND_TEST"):
            return Message(roomname, text, timestamp, username, systems, upperText, status=states.SOUND_TEST)
        if roomname not in self.rooms:
            return None


        message = Message(roomname, "", timestamp, username, systems, text, originalText)
        # May happen if someone plays > 1 account
        if message in self.knownMessages:
            message.status = states.IGNORE
            return message

        while parseShips(rtext):
            continue
        while parseUrls(rtext):
            continue
        while parseSystems(self.systems, rtext, systems):
            continue
        parsedStatus = parseStatus(rtext)
        status = parsedStatus if parsedStatus is not None else states.ALARM

        # If message says clear and no system? Maybe an answer to a request?
        if status == states.CLEAR and not systems:
            maxSearch = 2  # we search only max_search messages in the room
            for count, oldMessage in enumerate(oldMessage for oldMessage in self.knownMessages[-1::-1] if oldMessage.room == roomname):
                if oldMessage.systems and oldMessage.status == states.REQUEST:
                    for system in oldMessage.systems:
                        systems.add(system)
                    break
                if count > maxSearch:
                    break
        message.message = six.text_type(rtext)
        message.status = status
        self.knownMessages.append(message)
        if systems:
            for system in systems:
                system.messages.append(message)
        return message

    def _parseLocal(self, path, line):
        message = []
        """ Parsing a line from the local chat. Can contain the system of the char
        """
        charname = self.fileData[path]["charname"]
        if charname not in self.locations:
            self.locations[charname] = {"system": "?", "timestamp": datetime.datetime(1970, 1, 1, 0, 0, 0, 0)}

        # Finding the timestamp
        timeStart = line.decode().find("[") + 1
        timeEnds = line.decode().find("]")
        timeStr = line[timeStart:timeEnds].strip()
        timestamp = None
        try:
            timestamp = datetime.datetime.strptime(timeStr.decode(), "%Y.%m.%d %H:%M:%S")
        except Exception as e:
            logging.critical(e)
            return 
        # Finding the username of the poster
        userEnds = line.decode().find(">")
        if userEnds == -1:
            userEnds = len(line)-1
        username = line[timeEnds + 1:userEnds].strip()

        status = states.IGNORE
        # Finding the pure message
        text = line[userEnds + 1:].strip()  # text will the text to work an
        if username in ("EVE-System", "EVE System"):
            if ":" in text:
                system = text.split(":")[1].strip().replace("*", "").upper()
                status = states.LOCATION
            else:
                # We could not determine if the message was system-change related
                system = "?"
                status = states.IGNORE
            if timestamp > self.locations[charname]["timestamp"]:
                self.locations[charname]["system"] = system
                self.locations[charname]["timestamp"] = timestamp
                message = Message("", "", timestamp, charname, [system, ], "", "", status)

        # Solving new game logs user location where case
        if message == [] and status != states.LOCATION:
            text = line[timeEnds:].decode().strip().replace("*", "").lower()
            if "(none)" in text and "jumping" in text and "to" in text:
                system = text.split("to")[1].strip().upper()
                status = states.LOCATION 
                if self.locations[charname]["timestamp"] is None or timestamp > self.locations[charname]["timestamp"]:
                    self.locations[charname]["system"] = system
                    self.locations[charname]["timestamp"] = timestamp
                    message = Message("", "", timestamp, charname, [system, ], "", "", status)
				
        return message

    def fileModified(self, path):
        messages = []
        if path in self.ignoredPaths:
            return []
        # Checking if we must do anything with the changed file.
        # We only need those which name is in the rooms-list
        # EvE names the file like room_20140913_200737.txt, so we don't need
        # the last 20 chars. if file name is under 20 char it's most likely a game log 
        filename = os.path.basename(path)
  
        if len(filename) > 20:
            roomname = str(filename[:-20])
            if roomname.find('[') > -1:
                roomname = roomname[0:roomname.find('[')-1]
			
            if path not in self.fileData:
                # seems eve created a new file. New Files have 12 lines header
                self.fileData[path] = {"lines": 13}
            oldLength = self.fileData[path]["lines"]
            lines = self.addFile(path,'utf-16-le')
		
            if path in self.ignoredPaths:
                return []

            for line in lines[oldLength - 1:]:
                line = line.strip()
                line = line.encode('utf-8', 'ignore')
                if len(line) > 2:
                    message = None
                    if roomname == "Local":
                        message = self._parseLocal(path, line)   
                    else:
                        message = self._lineToMessage(line, roomname)
                    if message:
                        messages.append(message)
        else:
            # Game log parsing 
            if path not in self.fileData:
                self.fileData[path] = { "lines": 6} # Game logs have 6 lines header so we'll skip that 
            oldLength = self.fileData[path]["lines"]
            lines = self.addFile(path,'utf-8') 
     
            if path in self.ignoredPaths:
                return []
            for line in lines[oldLength - 1:]:
                line = line.strip()
                line = line.encode('ascii','ignore') 
                if len(line) > 2:
                    message = None 

                    message = self._parseLocal(path, line)
                    if message:
                        messages.append(message)
        return messages


class Message(object):
    def __init__(self, room, message, timestamp, user, systems, upperText, plainText="", status=states.ALARM):
        self.room = room  # chatroom the message was posted
        self.message = message  # the messages text
        self.timestamp = timestamp  # time stamp of the massage
        self.user = user  # user who posted the message
        self.systems = systems  # list of systems mentioned in the message
        self.status = status  # status related to the message
        self.upperText = upperText  # the text in UPPER CASE
        self.plainText = plainText  # plain text of the message, as posted
        # if you add the message to a widget, please add it to widgets
        self.widgets = []

    def __key(self):
        return (self.room, self.plainText, self.timestamp, self.user)

    def __eq__(x, y):
        return x.__key() == y.__key()

    def __hash__(self):
        return hash(self.__key())

import json
import logging
import os
import random
import socket
from logging.handlers import RotatingFileHandler

import protocol

host = "localhost"
port = 12000
# HEADERSIZE = 10

"""
set up fantom logging
"""
fantom_logger = logging.getLogger()
fantom_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s :: %(levelname)s :: %(message)s", "%H:%M:%S")
# file
if os.path.exists("./logs/fantom.log"):
    os.remove("./logs/fantom.log")
file_handler = RotatingFileHandler('./logs/fantom.log', 'a', 1000000, 1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
fantom_logger.addHandler(file_handler)
# stream
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
fantom_logger.addHandler(stream_handler)


class Player():
    move = ''
    character = {}
    rooms = {}

    def __init__(self):

        self.end = False
        # self.old_question = ""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def connect(self):
        self.socket.connect((host, port))

    def reset(self):
        self.socket.close()

    def select_character(self, answer):
        isolate, group = self.chose_strategy()
        if group > isolate:
            self.move = 'group'
            for room in self.rooms:
                if room['nbr_character'] == 1 or room['shadow']:
                    for character in answer:
                        for room_char in room['character']:
                            if character['color'] == room_char['color'] and character['suspect']:
                                self.character = character
                                return self.character
            for room in self.rooms:
                if room['nbr_character'] > 2 and not room['shadow']:
                    for character in answer:
                        for room_char in room['character']:
                            if character['color'] == room_char['color']:
                                self.character = character
                                return self.character
            for room in self.rooms:
                if room['nbr_character'] == 1 or room['shadow']:
                    for character in answer:
                        for room_char in room['character']:
                            if character['color'] == room_char['color']:
                                self.character = character
                                return self.character
            return answer[0]
        elif isolate > group:
            self.move = 'isolate'
            for room in self.rooms:
                if room['nbr_character'] == 2 and not room['shadow']:
                    for character in answer:
                        for room_char in room['character']:
                            if character['color'] == room_char['color'] and character['suspect']:
                                self.character = character
                                return self.character
            for room in self.rooms:
                if room['nbr_character'] >= 1 and not room['shadow']:
                    for character in answer:
                        for room_char in room['character']:
                            if character['color'] == room_char['color'] and character['suspect']:
                                self.character = character
                                return self.character
            for room in self.rooms:
                if room['nbr_character'] == 2 and not room['shadow']:
                    for character in answer:
                        for room_char in room['character']:
                            if character['color'] == room_char['color']:
                                for char in room['character']:
                                    if char['suspect'] and char['color'] != room_char['color']:
                                        self.character = character
                                        return self.character
            for room in self.rooms:
                if room['nbr_character'] >= 1 and not room['shadow']:
                    for character in answer:
                        for room_char in room['character']:
                            if character['color'] == room_char['color']:
                                self.character = character
                                return self.character
            return answer[0]
        self.character = answer[0]
        for char in answer:
            if char['suspect']:
                self.character = char
        for room in self.rooms:
            for character in room['character']:
                if character['color'] == self.character['color']:
                    if room['nbr_character'] > 1 and not room['shadow']:
                        self.move = 'isolate'
                    else:
                        self.move = 'group'
        return self.character

    def select_room_with_character(self, answers):
        for answer in answers:
            if self.rooms[answer]["nbr_character"] == 1 and self.rooms[answer]["character"][0]["suspect"] and not self.rooms[answer]["shadow"]:
                return answer
        for answer in answers:
            if self.rooms[answer]["nbr_character"] >= 1 and not self.rooms[answer]["shadow"]:
                return answer
        return answers[0]

    def select_room_without_character(self, answers):
        for answer in answers:
            if self.rooms[answer]["nbr_character"] == 0:
                return answer
        for answer in answers:
            if self.rooms[answer]["shadow"]:
                return answer
        return answers[0]

    def select_position(self, answer):
        if self.move == 'group':
            return self.select_room_with_character(answer)
        elif self.move == 'isolate':
            return self.select_room_without_character(answer)
        else:
            return answer[0]

    def chose_strategy(self):
        isolate = 0
        group = 0
        for room in self.rooms:
            if room["nbr_character"] == 1 or room['shadow']:
                for character in room["character"]:
                    if character["suspect"]:
                        isolate += 1
            else:
                for character in room["character"]:
                    if character["suspect"]:
                        group += 1
        return isolate, group

    def parse_room(self, game_state):
        result = []
        for i in range(10):
            room = {}
            character = []
            for j in range(len(game_state['characters'])):
                if game_state['characters'][j]['position'] == i:
                    character.append(game_state['characters'][j])
            if game_state['shadow'] == i:
                room["shadow"] = True
            else:
                room["shadow"] = False
            room["salle"] = i
            room["nbr_character"] = len(character)
            room["character"] = character
            result.append(room)
        return result

    def set_shadow(self, answer):
        isolate, group = self.chose_strategy()
        if group > isolate:
            i = 0
            for room in self.rooms:
                if room['nbr_character'] == 0:
                    return answer[i]
                i += 1
        else:
            i = 0
            for room in self.rooms:
                if room['nbr_character'] >= 2:
                    for char in room['character']:
                        if char['suspect']:
                            return i
                i += 1
        return 0

    def chose_answer(self, question_type, answer, game_state):
        if question_type == 'select character':
            self.rooms = self.parse_room(game_state)
            return self.select_character(answer)
        elif 'activate' in question_type and 'power' in question_type:
            return answer[0]
        elif question_type == 'select position':
            return self.select_position(answer)
        elif question_type == 'grey character power':
            self.rooms = self.parse_room(game_state)
            return self.set_shadow(answer)
        return answer[0]

    def answer(self, question):
        answer = question["data"]
        game_state = question["game state"]
        result = self.chose_answer(question['question type'], answer, game_state)
        print(question['question type'])
        print(self.chose_strategy())
        print(result)
        i = 0
        for ans in answer:
            if ans == result:
                return i
            i += 1
        return result

    def handle_json(self, data):
        data = json.loads(data)
        response = self.answer(data)
        bytes_data = json.dumps(response).encode("utf-8")
        protocol.send_json(self.socket, bytes_data)

    def run(self):

        self.connect()

        while self.end is not True:
            received_message = protocol.receive_json(self.socket)
            if received_message:
                self.handle_json(received_message)
            else:
                print("no message, finished learning")
                self.end = True


p = Player()

p.run()

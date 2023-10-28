"""Interface with the lichess.org api"""
import asyncio
import datetime
import threading
import time

import berserk
import chess
import logging
log = logging.getLogger("ChessnutPy")

class LiChess:
    def __init__(self, token):
        try:
            self.session = berserk.TokenSession(token)
            self.client = berserk.Client(self.session)
            self.account = self.client.account.get()
            print(self.account)
            self.game_id = None
            self.game = None
            self.game_info = None
        except berserk.exceptions.BerserkError as e:
            log.error(f"Couldn't connect to LiChess! ({e})")

    def reset(self):
        self.game_id = None
        self.game = None
        self.game_info = None

    def seek_game(self, clock_time=0, increment=0, rated=False, color='random', rating_range='1000-2000'):
        def acc_fun():
            for event in self.client.board.stream_incoming_events():
                if self.accept_game(event):
                    return
        acc_thread = threading.Thread(target=acc_fun)
        acc_thread.start()
        print(f'{clock_time} {increment}, {rated} {color} {rating_range}')
        self.client.board.seek(float(clock_time), increment, rated=rated, rating_range=rating_range, color=color)
        print(f'first done')
        acc_thread.join()

    def accept_game(self, event, accept_fun=lambda event: True):
        if event['type'] == 'gameStart' and accept_fun(event['game']):
            self.game_id = event['game']['id']
            game = LiChessGame(self.client, self.game_id)
            self.game = game
            self.game_info = event['game']
            game.start()
            msg = "Hey I'm using a ChessNut Air board over bluetooth and cannot see if you want to call a draw." + \
                  " Sorry for the inconvenience (:"
            self.client.board.post_message(self.game_id, msg)
            return True
        return False

    def await_challenge(self, is_polite=True,
                        challenge_accept_fun=lambda event: True,  # ex. event['challenger']['id'] == 'bierliebhaber92'
                        game_accept_fun=lambda event: True):
        print("start of C request")
        for event in self.client.board.stream_incoming_events():
            print('EVENT: ', event)
            if event['type'] == 'challenge':
                c_id = event['challenge']['id']
                if challenge_accept_fun(event['challenge']):
                    self.client.challenges.accept(c_id)
                elif is_polite:
                    self.client.challenges.decline(c_id)
            if self.accept_game(event, accept_fun=game_accept_fun):
                return
        print("end of C request")

    def make_move(self, move: chess.Move):
        if self.game:
            self.client.board.make_move(self.game_id, move.uci())

    def abort_game(self):
        if self.game:
            self.client.board.abort_game(self.game_id)
            self.reset()

    def resign_game(self):
        if self.game:
            self.client.board.resign_game(self.game_id)
            self.reset()

    async def opponent_move(self, sleep_fun=lambda: asyncio.sleep(0.1)):
        if self.game:
            while self.game.move_num < 0 \
                    or (self.game.move_num % 2 == 1 and self.game_info['color'] == 'white')\
                    or (self.game.move_num % 2 == 0 and self.game_info['color'] == 'black'):
                if self.game.ended:
                    return None
                await sleep_fun()
            move = self.game.last_move
            return move
        return None

    def get_white_time_left(self):
        if self.game and self.game.last_time_update:
            if self.game.move_num % 2 == 0:
                return self.game.white_time+self.game.last_time_update-time.time()
            else:
                return self.game.white_time
        else:
            return 0

    def get_black_time_left(self):
        if self.game and self.game.last_time_update:
            if self.game.move_num % 2 == 1:
                return self.game.black_time+self.game.last_time_update-time.time()
            else:
                return self.game.black_time
        else:
            return 0


class LiChessGame(threading.Thread):
    def __init__(self, client, game_id, **kwargs):
        super().__init__(**kwargs)
        self.game_id = game_id
        self.client = client
        self.stream = client.board.stream_game_state(game_id)
        self.current_state = next(self.stream)
        self.last_event = None
        self.chat = ""
        self.last_move = None
        self.move_num = -1
        self.black_time = None
        self.white_time = None
        self.last_time_update = None
        self.ended = False
        self.winner = None
        self.offered_draw = False
        self.offered_undo = False

    def run(self):
        for event in self.stream:
            if event['type'] == 'gameState':
                self.handle_state_change(event)
            elif event['type'] == 'chatLine':
                self.handle_chat_line(event)

    def handle_state_change(self, game_state):
        self.last_event = game_state
        log.debug(f'LiChess GAMESTATE: {game_state}')
        moves = game_state['moves'].split()
        if game_state['status'] != 'started':
            self.ended = True
            try:
                self.winner = chess.WHITE if game_state['winner'] == 'white' else chess.BLACK
            except KeyError:
                pass
        self.last_move = moves[-1]
        self.move_num = len(moves)
        self.last_time_update = time.time()
        self.black_time = game_state['btime'].timestamp()
        self.white_time = game_state['wtime'].timestamp()

    def handle_chat_line(self, chat_line):
        self.chat += f"{chat_line['username']}: {chat_line['text']}\n"
        print(f"LiChess CHAT: {chat_line}")

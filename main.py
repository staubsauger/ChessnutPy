import asyncio
from data2fen import convert_to_fen
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from ChessnutAir import ChessnutAir, loc_to_pos
from GameOfChess import GameOfChess
import chess
import random


class Game(ChessnutAir):
    def __init__(self, board_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", turn="w", castle="KQkq",
                 player_color="w"):
        ChessnutAir.__init__(self)
        self.target_move = None
        self.move_end = None
        self.move_start = None
        self.running = False
        self.tick = False
        self.to_blink = []
        self.to_light = []
        self.board = chess.Board(f"{board_fen} {turn} {castle} - 0 1")
        self.target_fen = ""
        self.waiting_for_move = True
        if turn == player_color:
            self.player_turn = True
        else:
            self.player_turn = False

    def boardstate_as_fen(self):
        self.cur_fen = convert_to_fen(self.boardstate)
        return self.cur_fen

    async def piece_down(self, location, piece_id):
        # location = 0oyx 0x77
        # a1 = 63 = 7 7 -> 7=a 6=b 5=c 4=d 3=e 2=f 1=g 0=h
        # e4 = 35 = 3 4 ->
        # g6 = 17 = 1 2 ->
        pos = loc_to_pos(location)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} down")
        if self.move_start is not None:
            self.to_light.remove(self.move_start[0])
            await self.change_leds(self.to_light)
        if self.move_start is not None and self.move_start[0] != pos:
            self.move_end = (pos, p_str)
        else:
            self.to_blink = []
        print(self.boardstate_as_fen())

    async def piece_up(self, location, piece_id):
        pos = loc_to_pos(location)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} up")
        self.to_light.append(pos)
        await self.change_leds(self.to_light)
        self.move_end = None
        self.move_start = (pos, p_str)
        for move in self.board.legal_moves:
            m_str = f"{move}"
            from_square = m_str[:2]
            if from_square == pos:
                self.to_blink.append(m_str[2:])

    async def game_loop(self):
        await asyncio.sleep(1)
        self.running = True
        while self.running:
            self.tick = not self.tick
            if self.to_blink:
                if self.tick:
                    await self.change_leds(self.to_blink + self.to_light)
                else:
                    await self.change_leds(self.to_light)
            await asyncio.sleep(0.5)

            if self.move_start is not None and self.move_end is not None\
                    and self.move_start != self.move_end:
                move = self.move_start[0] + self.move_end[0]
                if self.target_move is not None:
                    if move == self.target_move:
                        self.target_move = None
                        self.move_start = None
                        self.move_end = None
                        self.to_blink = []
                        print("move reset")
                    continue
                if self.player_turn:
                    if self.board.is_legal(chess.Move.from_uci(move)):
                        self.board.push_san(move)
                        print(self.board)
                        self.to_blink = []
                        self.player_turn = False
                    else:
                        self.target_move = self.move_end[0]+self.move_start[0]
                        self.to_blink.extend((self.move_start[0], self.move_end[0]))
                        print(f"illegal move {move}\n{self.board}")
                self.move_start = None
                self.move_end = None

            elif not self.player_turn:
                    # generate move
                    move = self.board.legal_moves[len(self.board.legal_moves)-1]
                    self.target_move = move
                    self.to_light = [move[:2], move[2:]]
                    self.player_turn = True




async def go():
    b = Game()
    # c = GameOfChess(b.boardstate)
    await b.discover()
    await b.run()    

asyncio.run(go())

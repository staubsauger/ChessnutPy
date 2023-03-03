import asyncio
from data2fen import convert_to_fen
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from ChessnutAir import ChessnutAir, loc_to_pos
from GameOfChess import GameOfChess
import chess
from chess.engine import Cp
import random

from fencompare import compare_chess_fens, fen_diff_leds

"""
Mindmap:

aufstellung der startposition = neues game
wenn stellung aufgestellt, dann ist der player turn = der letzte könig der gesetzt wurde
analysefunktion bzw. schiedsrichterfunktion


"""
class Game(ChessnutAir):
    def __init__(self, board_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", turn="w", castle="KQkq",
                 player_color="w"):
        ChessnutAir.__init__(self)
        self.target_move = None
        self.move_end = None
        self.move_start = None
        self.running = False
        self.tick = False
        self.castling = False
        self.to_blink = []
        self.to_light = []
        self.board = chess.Board(f"{board_fen} {turn} {castle} - 0 1")
        self.target_fen = ""
        self.waiting_for_move = True
        self.undo_loop = False
        if turn == player_color:
            self.player_turn = True
        else:
            self.player_turn = False
        self.ai_turn = not self.player_turn
        self.game = GameOfChess()

    def boardstate_as_fen(self):
        self.cur_fen = convert_to_fen(self.boardstate)
        return self.cur_fen

    async def piece_down(self, location, piece_id):
        # location = 0oyx 0x77
        # a1 = 63 = 7 7 -> 7=a 6=b 5=c 4=d 3=e 2=f 1=g 0=h
        # e4 = 35 = 3 4 ->
        # g6 = 17 = 1 2 ->
        pos = loc_to_pos(location)
        print("Location", pos)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} down")
        if self.move_start is not None:
            self.to_light = []
            await self.change_leds(self.to_light)
            if self.move_start[0] != pos:
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
        if self.move_start is None:
            self.move_start = (pos, p_str)
        elif self.move_start[0] != pos:
            self.move_start = [(pos, p_str), self.move_start]
            return
        for move in self.board.legal_moves:
            m_str = f"{move}"
            from_square = m_str[:2]
            if from_square == pos:
                self.to_blink.append(m_str[2:])
            to_square = m_str[2:]
            if to_square == pos:
                self.to_blink.append(m_str[:2])
        if len(self.board.move_stack) > 0:
            undo = f"{self.board.peek()}"
            if undo[2:] == pos:
                self.to_blink.append(undo[:2])


    async def blink_tick(self):
        self.tick = not self.tick
        if self.tick:
            await self.change_leds(self.to_blink+self.to_light)
        else:
            await self.change_leds(self.to_light)

    async def fix_board(self):
        diff = compare_chess_fens(self.board.fen(), self.boardstate_as_fen())
        if diff:
            print("board incorrect!\nplease fix")
            while diff:
                led_pairs = fen_diff_leds(diff)
                first = led_pairs[0]
                if len(first) == 1:
                    self.to_blink = first
                    self.to_light = []
                else:
                    if self.castling and len(led_pairs) > 1 and led_pairs[1][0].startswith("e"):
                        self.to_light = led_pairs[1]
                    else:
                        self.to_light = first
                    self.to_blink = []
                await self.blink_tick()
                await asyncio.sleep(0.2)
                diff = compare_chess_fens(self.board.fen(), self.boardstate_as_fen())
            print("board fixed!")
            await asyncio.sleep(0.5)
        else:
            test = self.boardstate_as_fen()
            print(f"board correct:\n{chess.Board(test)}")
        self.castling = False
        self.move_start = self.move_end = None
        self.to_light = self.to_blink = []
        if self.undo_loop and len(self.board.move_stack) > 0:
            next_undo = f"{self.board.peek()}"
            self.to_light = [next_undo[:2], next_undo[2:]]
        await self.change_leds([])

    async def game_loop(self):
        await asyncio.sleep(1)  # wait for board to settle
        print("Board settled", self.board)
        await self.fix_board()

        self.running = True
        while self.running:
            await self.blink_tick()
            if self.board.is_checkmate():
                print("checkmate!")
                self.running = False
                self.game.quitchess()
                continue

            await asyncio.sleep(0.3)

async def go():
    b = Game() #board_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", turn='w', player_color='w')
    # c = GameOfChess(b.boardstate)
    while not b.device:
        await b.discover()
    try:
        await b.run()
    # except Exception:
    #   print(b.board.fen())
    except KeyboardInterrupt:
        print(b.board.fen())

asyncio.run(go())

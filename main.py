import asyncio
from data2fen import convert_to_fen
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from ChessnutAir import ChessnutAir, loc_to_pos
from GameOfChess import GameOfChess
import chess


class Game(ChessnutAir):
    def __init__(self, board_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", turn="w", castle="KQkq",
                 player_color="w"):
        ChessnutAir.__init__(self)
        self.move_end = None
        self.move_start = None
        self.running = False
        self.tick = False
        self.to_blink = ["a3", "b4", "c7", "h3"]
        self.to_light = ["a5"]
        self.cur_fen = ""
        self.target_fen = ""

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
        if self.move_start != None:
            self.to_light.remove(self.move_start[0])
        self.move_end = (pos, p_str)
        print(self.boardstate_as_fen())

    async def piece_up(self, location, piece_id):
        pos = loc_to_pos(location)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} up")
        self.to_light.append(pos)
        self.move_end = None
        self.move_start = (pos, p_str)

    async def game_loop(self):
        self.running = True
        while self.running:
            self.tick = not self.tick
            if self.tick:
                await self.change_leds(self.to_blink + self.to_light)
            else:
                await self.change_leds(self.to_light)
            await asyncio.sleep(0.5)



async def go():
    b = Game()
    # c = GameOfChess(b.boardstate)
    await b.discover()
    await b.run()    

asyncio.run(go())

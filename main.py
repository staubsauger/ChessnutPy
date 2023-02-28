import asyncio
from data2fen import convert_to_fen
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from ChessnutAir import ChessnutAir
from GameOfChess import GameOfChess


class Board(ChessnutAir):
    def __init__(self):
        ChessnutAir.__init__(self)
        self.running = False
        self.tick = False
        self.to_blink = ["a3", "b4", "c7", "h3"]
        self.to_light = ["a5"]
        self.cur_fen = ""
        self.target_fen = ""

    def boardstate_as_fen(self):
        fen = convert_to_fen(self.boardstate)
        return fen

    async def piece_down(self, location, id):
        # location = 0oyx 0x77
        # a1 = 63 = 7 7 -> 7=a 6=b 5=c 4=d 3=e 2=f 1=g 0=h
        # e4 = 35 = 3 4 ->
        # g6 = 17 = 1 2 ->
        x = "hgfedcba"[location % 8]
        y = 8-(location//8)

        print(f"piece: {convertDict[id]} at {location} down pos: {x}{y}")
        print(self.boardstate_as_fen()) # location -> pos: x = location%8, y = location//8

    async def piece_up(self, location, id):
        print(f"piece: {convertDict[id]} at {location} up")

    async def game_loop(self):
        self.running = True
        while self.running:
            self.tick = not self.tick
            if self.tick:
                await self.change_leds(self.to_blink + self.to_light)
            else:
                await self.change_leds(self.to_light)
            await asyncio.sleep(1)

async def go():
    b = Board()
    # c = GameOfChess(b.boardstate)
    await b.discover()
    await b.run()    

asyncio.run(go())


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
        self.to_light = []
        self.cur_fen = ""
        self.target_fen = ""

    def boardstate_as_fen(self):
        fen = convert_to_fen(self.boardstate)
        return fen

    async def piece_down(self, location, id):
        print(f"piece: {convertDict[id]} at {location} down")

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


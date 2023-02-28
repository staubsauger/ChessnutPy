import asyncio
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from ChessnutAir import ChessnutAir
from GameOfChess import GameOfChess

class Board(ChessnutAir):
    def __init__(self):
        super.__init__()
        self.running = False
        self.boardstate = ""
        self.tick = False
        self.to_blink = ["a3", "b4", "c7", "h3"]

    async def piece_down(self, location, id):
        print(f"piece: {convertDict[id]} at {location} down")
        # print(self.returnboardstate())
        self.turnLedOnOn("a4")
        # print("OnLeds", self.onledsarr)

    async def piece_up(self, location, id):
        print(f"piece: {convertDict[id]} at {location} up")

    async def game_loop(self):
        self.running = True
        while self.running:
            self.tick = not self.tick
            #print("Tick: ", self.tick)
            if self.tick:
                await self.change_leds(self.to_blink)
            else:
                await self.change_leds([])
            await asyncio.sleep(1)

async def go():
    b = Board()
    # c = GameOfChess(b.boardstate)
    await b.discover()
    await b.run()    

asyncio.run(go())


import asyncio
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from ChessnutAir import ChessnutAir
from GameOfChess import GameOfChess

class Board(ChessnutAir):
    async def piece_down(self, location, id):
        print(f"piece: {convertDict[id]} at {location} down")
        # print(self.returnboardstate())
        self.turnLedOnOn("a4")
        # print("OnLeds", self.onledsarr)

    async def piece_up(self, location, id):
        print(f"piece: {convertDict[id]} at {location} up")
        
    async def showmoveonboard(self, bytearr):
        await self.connection.write_gatt_char(WRITECHARACTERISTICS, bytearr)

async def go():
    b = Board()
    # c = GameOfChess(b.boardstate)
    await b.discover()
    await b.run()    

asyncio.run(go())


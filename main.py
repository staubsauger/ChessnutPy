import asyncio
import sys

from aiohttp import web

from BoardGame import BoardGame
import chess.engine
from bleak import BleakError

from WebInterface import start_server

# noinspection SpellCheckingInspection
"""
Mindmap:

aufstellung der startposition = neues game
wenn stellung aufgestellt, dann ist der player turn = der letzte könig der gesetzt wurde
analysefunktion bzw. schiedsrichterfunktion

funktionsweise pi:
-an
- programm wird gestartet -> sucht nach board
-> vielleicht shutdown nach 5 min
- findet board -> ließt startpos aus
- fragt nach spielerfarbe
- startet game 
- wenn matt dann restart gameloop
- wenn beide könige in der mitte (diagonal oder nebeneinander) restart gameloop, 
    wenn beide weißen damen nebeneinander shutdown
"""


# noinspection SpellCheckingInspection
async def go():
    dirs = sys.argv[1:]
    if len(dirs) == 3:
        suggestion_book_dir, engine_dir, engine_suggest_dir = dirs
    else:
        suggestion_book_dir = "/usr/share/scid/books/Elo2400.bin"  # maybe make these 3 vars configurable by argument
        engine_dir = "/home/rudi/Games/schach/texel-chess/texel/build/texel"
        engine_suggest_dir = "stockfish"
    # t, e = await chess.engine.popen_uci(engine_dir)
    # move = asyncio.create_task(e.play(chess.Board(), chess.engine.Limit(time=10.5)))
    b = BoardGame(show_valid_moves=True,
                  suggestion_book_dir=suggestion_book_dir,
                  engine_dir=engine_dir,
                  engine_suggest_dir=engine_suggest_dir,
                  eco_file='scid.eco')
    await b.connect()
    try:
        run_task = asyncio.create_task(b.run())
        return await start_server(b)
        # while not run_task.done():
        #     await asyncio.sleep(1.0)
    except BleakError:
        print("Board Disconnected. Retrying connection.")
        run_task = asyncio.create_task(b.run())
        quit()
    except KeyboardInterrupt:
        print(b.board.fen())
        await b.stop_handler()
        b.game.quit_chess_engines()
        quit()

if __name__ == "__main__":
    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    try:
        if "no-server" in sys.argv:
            sys.argv.remove("no-server")
            asyncio.run()
        else:
            host = list(filter(lambda arg: arg.startswith("host:"), sys.argv))
            if len(host) > 0:
                hosts = host
                for h in hosts:
                    sys.argv.remove(h)
                host = hosts[0].split(':')[1:]
                web.run_app(go(), host=host.append('localhost'), port=8080)
            else:
                web.run_app(go(), host='localhost', port=8080)
    except KeyboardInterrupt:
        pass
    asyncio.get_event_loop().close()

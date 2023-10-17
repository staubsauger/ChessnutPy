import ast
import asyncio
import sys
import socket

from aiohttp import web

from BoardGame import BoardGame
import chess.engine
from bleak import BleakError

from WebInterface import start_server
import configargparse

# noinspection SpellCheckingInspection

options = None


# noinspection SpellCheckingInspection
async def go():
    b = BoardGame(show_valid_moves=options.show_valid_moves,
                  suggestion_book_dir=options.suggestion_book_dir,
                  engine_dir=options.engine_cmd,
                  engine_suggest_dir=options.engine_suggest_cmd,
                  eco_file=options.eco_file,
                  engine_cfg=ast.literal_eval(options.engine_cfg),
                  experimental_dragging_detection=options.experimental_dragging_detection,
                  experimental_dragging_timeout=options.experimental_dragging_timeout,
                  play_animations=options.play_animations,
                  engine_time=float(options.engine_time) if options.engine_time != 'None' else None,
                  engine_nodes=int(options.engine_nodes) if options.engine_nodes != 'None' else None,
                  engine_depth=int(options.engine_depth) if options.engine_depth != 'None' else None,
                  sug_depth=int(options.sug_depth) if options.sug_depth != 'None' else None,
                  sug_nodes=int(options.sug_nodes) if options.sug_nodes != 'None' else None,
                  sug_time=float(options.sug_time) if options.sug_time != 'None' else None,
                  show_would_have_done_move=options.show_would_have_done_move,
                  lichess_token=options.lichess_token)
    await b.connect()
    run_task = asyncio.create_task(b.run())
    if not options.no_server:
        return await start_server(b)
    while not run_task.done():
        await asyncio.sleep(1.0)

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.settimeout(0)
    # noinspection PyBroadException
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


if __name__ == "__main__":
    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    p = configargparse.ArgParser(default_config_files=["./Docs/default.config", '~/.config/chessnutair.config'],
                                 ignore_unknown_config_file_keys=False)
    p.add_argument("--no_server", default=False, action="store_true")
    p.add_argument("--hosts", default='auto-hosts', help='ip1:ip2, or auto-hosts to use local address')
    p.add_argument('-p', '--port', default=8080, type=int)
    p.add_argument('-e', "--engine_cmd", default="stockfish")
    p.add_argument('--engine_cfg', default="{}", help="Engine config dict")
    p.add_argument('--engine_time', default=0.5, help='Time the engine has to think')
    p.add_argument('--engine_depth', default=None, help='How deep can the engine calculate ahead')
    p.add_argument('--engine_nodes', default=None, help='How many nodes can the engine use')
    p.add_argument('--sug_time', default=5, help='Time the suggestions engine has to think')
    p.add_argument('--sug_depth', default=None, help='How deep can the suggestions engine calculate ahead')
    p.add_argument('--sug_nodes', default=None, help='How many nodes can the suggestions engine use')
    p.add_argument('--no_suggestions', default=False, action="store_true", help='disable suggestions')
    p.add_argument('--engine_suggest_cmd', default='stockfish')
    p.add_argument('--suggestion_book_dir', default='./Docs/Elo2400.bin')
    p.add_argument('--eco_file', default='./Docs/scid.eco')
    p.add_argument('--lichess_token', default='')
    p.add_argument('--experimental_dragging_detection', default=False, action="store_true")
    p.add_argument('--experimental_dragging_timeout', default=0.3, type=float)
    p.add_argument('--show_valid_moves', default=False, action="store_true")
    p.add_argument('--play_animations', default=False, action="store_true")
    p.add_argument('--show_would_have_done_move', default=False, action='store_true')
    # TODO: flags should never default to True otherwise they are not changeable
    options = p.parse_args()
    p.print_values()
    try:
        if options.no_server:
            asyncio.run(go())
        elif options.hosts == 'auto-hosts':
            
            try:
                host = get_ip()
                print(host)
                hosts = [host, 'localhost'] if host != '127.0.0.1' else host
                web.run_app(go(), host=hosts, port=8080)
            except:
                print("No network found.")
                options.no_server = True
                options.lichess_token = ''
                asyncio.run(go())

        elif len(options.hosts) > 0:
            
            try:
                hosts = options.hosts
                host = hosts[0].split(':')[1:]
                host.append('localhost')
                web.run_app(go(), host=host, port=options.port)
            except:
                print("No network found.")
                options.no_server = True
                options.lichess_token = ''
                asyncio.run(go())
        else:
            web.run_app(go(), host='localhost', port=8080)
    except KeyboardInterrupt:
        pass
    try:
        asyncio.get_event_loop().close()
    except RuntimeError:
        pass

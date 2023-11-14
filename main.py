import ast
import asyncio
import sys
import atexit
import signal
import socket

from aiohttp import web

from BoardGame import BoardGame
import chess.engine

from WebInterface import start_server
import configargparse
from platformdirs import user_config_dir

import logging
from os import replace, path

log = logging.getLogger("ChessnutPy")

# noinspection SpellCheckingInspection

options = None


# noinspection SpellCheckingInspection
async def go():
    try:
        options.engine_cfg = ast.literal_eval(options.engine_cfg)
    except:
        log.warning(f"Couldn't parse engine_cfg: {options.engine_cfg}")
        options.engine_cfg = {}
    try:
        options.sug_engine_cfg = ast.literal_eval(options.sug_engine_cfg)
    except:
        log.warning(f"Couldn't parse engine_cfg: {options.sug_engine_cfg}")
        options.sug_engine_cfg = {}
    options.engine_nodes = int(
        options.engine_nodes) if options.engine_nodes != 'None' else None
    options.engine_depth = int(
        options.engine_depth) if options.engine_depth != 'None' else None
    options.sug_depth = int(
        options.sug_depth) if options.sug_depth != 'None' else None
    options.sug_nodes = int(
        options.sug_nodes) if options.sug_nodes != 'None' else None
    b = BoardGame(options)
    await b.connect()
    run_task = asyncio.create_task(b.run())

    def print_trace_and_quit(fut):
        if fut.exception():
            log.error(fut.exception(), exc_info=True)
        sys.exit(0)

    run_task.add_done_callback(print_trace_and_quit)
    if not options.no_server:
        return await start_server(b)
    while not run_task.done():
        await asyncio.sleep(1.0)


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    # noinspection PyBroadException
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = None
    finally:
        s.close()
    return IP


def save_config(config):
    with open(user_config_dir('chessnutair.config'), 'w') as file:
        for k, v in config.__dict__.items():
            if k == "save_function":
                continue
            v = v if not isinstance(v, str) else f'"{v}"'
            file.write(f"{k} = {v}\n")
        log.info(f"Wrote config to {user_config_dir('chessnutair.config')}")


if __name__ == "__main__":
    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    p = configargparse.ArgParser(default_config_files=["./Docs/default.config", user_config_dir('chessnutair.config')],
                                 ignore_unknown_config_file_keys=False)
    p.add_argument("--no_server", default=False, action="store_true")
    p.add_argument("--hosts", default='auto-hosts',
                   help='ip1:ip2, or auto-hosts to use local address')
    p.add_argument('-p', '--port', default=8080, type=int)
    p.add_argument('-e', "--engine_cmd", default="stockfish")
    p.add_argument('--engine_cfg', default="{}", help="Engine config dict")
    p.add_argument('--engine_time', default=0.5,
                   help='Time the engine has to think', type=float)
    p.add_argument('--engine_depth', default=None,
                   help='How deep can the engine calculate ahead')
    p.add_argument('--engine_nodes', default=None,
                   help='How many nodes can the engine use')
    p.add_argument('--sug_engine_cfg', default="{}", help="Engine config dict")
    p.add_argument('--sug_time', default=5.0,
                   help='Time the suggestions engine has to think', type=float)
    p.add_argument('--sug_depth', default=None,
                   help='How deep can the suggestions engine calculate ahead')
    p.add_argument('--sug_nodes', default=None,
                   help='How many nodes can the suggestions engine use')
    p.add_argument('--no_suggestions', default=False,
                   action="store_true", help='disable suggestions')
    p.add_argument('--engine_suggest_cmd', default='stockfish')
    p.add_argument('--suggestion_book_dir', default='./Docs/Elo2400.bin')
    p.add_argument('--engine_ext_book_dir', default='./Docs/Elo2400.bin')
    p.add_argument('--engine_use_ext_book', default=False, action="store_true")
    p.add_argument('--eco_file', default='./Docs/scid.eco')
    p.add_argument('--lichess_token', default='')
    p.add_argument('--dragging_detection', default=False, action="store_true")
    p.add_argument('--dragging_timeout', default=0.3, type=float)
    p.add_argument('--show_valid_moves', default=False, action="store_true")
    p.add_argument('--play_animations', default=False, action="store_true")
    p.add_argument('--show_would_have_done_move',
                   default=False, action='store_true')
    p.add_argument('--logfile', default="log.log")
    p.add_argument('--username', default="user",
                   help='Name of the player when creating PGN files')
    # TODO: flags should never default to True otherwise they are not changeable
    options = p.parse_args()
    options.save_function = lambda: save_config(options)

    if path.isfile(options.logfile):
        replace(options.logfile, options.logfile+".1")
    with open(options.logfile, 'w') as lf:
        p.print_values(file=lf)
    logging.basicConfig(filename=options.logfile,
                        filemode='a', level=logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    def exit_handler():
        save_config(options)

    def kill_handler(*args):
        sys.exit(0)
    atexit.register(exit_handler)
    for s in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGABRT]:
        signal.signal(s, kill_handler)
    try:
        if options.no_server:
            asyncio.run(go())
        elif options.hosts == 'auto-hosts':
            host = get_ip()
            print(host)
            hosts = [host, 'localhost'] if host else 'localhost'
            web.run_app(go(), host=hosts, port=options.port)
        elif len(options.hosts) > 0:
            hosts = options.hosts
            host = hosts[0].split(':')[1:]
            if not ('localhost' in host or '127.0.0.1' in host):
                host.append('localhost')
            web.run_app(go(), host=host, port=options.port)
        else:
            web.run_app(go(), host='localhost', port=options.port)
    except KeyboardInterrupt:
        pass
    try:
        asyncio.get_event_loop().close()
    except RuntimeError:
        pass

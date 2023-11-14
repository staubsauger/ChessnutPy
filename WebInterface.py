import ast
import pathlib
import json
import re
import select
import aiohttp
import multidict

import chess.svg
import chess.engine
from aiohttp import web
import chess
from BoardGame import BoardGame
from bleak import BleakError
import logging
import time

log = logging.getLogger("ChessnutPy")


def svg_board(board, player_color):
    fill = {}
    if board.is_check():
        fill = {board.king(board.turn): 'red'}
    attackable = filter(lambda pos: (board.piece_at(pos) and board.piece_at(pos).color == board.turn and
                                     board.is_attacked_by(not board.turn, pos)),
                        chess.SQUARES)
    for square in attackable:
        fill[square] = 'yellow'
    svg = chess.svg.board(board, size=350, lastmove=board.move_stack[-1] if len(board.move_stack) > 0 else None,
                          # colors={'margin': '#01010101', 'square light': '#ff0000', 'square dark': '#7070ff', 'coord': '#00ff00' }
                          fill=fill, flipped=not player_color,
                          )
    return svg


class BoardAppHandlers:
    def __init__(self, board: BoardGame):
        self.index_template = './WebInterface_Helpers/main_page.html'
        self.engine_settings = './WebInterface_Helpers/engine_settings.html'
        self.online_game = './WebInterface_Helpers/online_game.html'
        self.move_stack = './WebInterface_Helpers/move_stack.html'
        self.counter_openings = './WebInterface_Helpers/counter_openings.html'
        self.css = './WebInterface_Helpers/mystyle.css'
        self.game_board: BoardGame = board
        self.last_svg_board_fen = None
        self.last_svg_board = None
        self.last_opening = None
        self.last_move_stack = None
        self.last_move_stack_text = None

    async def index(self, request):
        return web.FileResponse(self.index_template)

    async def css_handler(self, request):
        return web.FileResponse(self.css)

    async def online_game_handler(self, request):
        return web.FileResponse(self.online_game)

    async def debug_handler(self, request):
        data = {}
        for e in self.game_board.__dict__:
            data[str(e)] = str(self.game_board.__dict__[e]).strip('\n')
        res = web.json_response(data=data)
        return res

    async def board_svg_handler(self, request):
        # start_time = time.perf_counter_ns()
        cur_fen = self.game_board.board.board_fen()
        if not self.last_svg_board_fen == cur_fen:
            self.last_svg_board = svg_board(
                self.game_board.board, self.game_board.player_color)
            self.last_svg_board_fen = cur_fen

        res = web.Response(text=self.last_svg_board)
        res.content_type = 'image/svg+xml'
        # log.warning(f"svg_board took {(time.perf_counter_ns()-start_time)//1_000_000} ms")
        return res

    async def opening_handler(self, request):
        data = self.game_board.engine_manager.print_openings(
            self.game_board.board)
        if data != "No opening found.":
            self.last_opening = data
        return web.json_response(self.last_opening)

    async def move_stack_frame_handler(self, request) -> web.Response:
        return web.FileResponse(self.move_stack)

    async def move_stack_handler(self, request) -> web.Response:
        data: list[chess.Move] = self.game_board.board.move_stack
        if data == self.last_move_stack:
            return web.Response(text=self.last_move_stack_text)
        starting_board: chess.Board = self.game_board.board.copy()
        if len(starting_board.move_stack) == 0:
            return web.Response()
        while len(starting_board.move_stack) > 0:
            starting_board.pop()
        moves = starting_board.variation_san(data)
        bm = re.sub(r'\d+\.', r'<b>\g<0></b>', moves)
        self.last_move_stack = data.copy()
        self.last_move_stack_text = bm
        return web.Response(text=bm)

    async def last_score_handler(self, request):
        return web.json_response(self.game_board.last_score / 100 if self.game_board.last_score else None)

    async def read_board_handler(self, request):
        await self.game_board.exit_read_board_and_select_color()
        return web.Response(status=303)

    async def start_online_challenge_handler(self, request):
        await self.game_board.exit_read_board_and_select_color(wants_online='challenge')
        return await self.online_game_handler(request)

    async def online_chat_handler(self, request):
        text = self.game_board.lichess.game.chat if self.game_board.lichess and self.game_board.lichess.game else ''
        return web.Response(text=text)

    async def seek_game_handler(self, request):
        def safe_dict_get(dic, attr):
            try:
                val = dic[attr]
                if all(map(lambda c: c.isdigit(), val)):
                    val = int(val)
                return val
            except KeyError:
                return None
        # this is a POST request
        # str that is dict of cfg
        data = await request.post()
        clock_time = safe_dict_get(data, 'time')
        increment = safe_dict_get(data, 'increment')
        rated = safe_dict_get(data, 'rated')
        rated = rated == 'on'
        rating_range = safe_dict_get(data, 'rating_range')
        color = safe_dict_get(data, 'color')
        seek_info = (clock_time, increment, rated, color, rating_range)
        await self.game_board.exit_read_board_and_select_color(wants_online='seek', seek_info=seek_info)
        return await self.online_game_handler(request)

    async def counter_openings_frame_handler(self, request):
        return web.FileResponse(self.counter_openings)

    async def counter_openings_handler(self, request):
        def move_to_opening(entry):
            board = self.game_board.board.copy()
            board.push(entry.move)
            opening = self.game_board.engine_manager.print_openings(board)
            return f'<div title="weight: {entry.weight}"> {f"{opening[0][0]}: {opening[0][1]}" if opening else "Unamed"} -> {entry.move.uci()} </div>'
        moves = [move_to_opening(
            e) for e in self.game_board.engine_manager.get_book_moves(self.game_board.board)]
        res = web.json_response(data=moves)
        return res

    async def get_battery(self, request):
        try:
            await self.game_board.request_battery_status()
        except BleakError:
            return web.json_response(data=[-1, 0])
        data = [1 if self.game_board.charging else 0,
                self.game_board.charge_percent]
        return web.json_response(data=data)

    async def time_handler(self, request):
        data = [-1, -1]
        if self.game_board.lichess:
            data = [self.game_board.lichess.get_white_time_left(
            ), self.game_board.lichess.get_black_time_left()]
        return web.json_response(data=data)


class EngineAppHandlers:
    def __init__(self, board: BoardGame) -> None:
        self.engine_settings = './WebInterface_Helpers/engine_settings.html'
        self.game_board: BoardGame = board

    async def add_engine_settings(self, text, is_suggestion, engine_cfg) -> str:
        engine = self.game_board.engine_manager.engine_suggest\
            if is_suggestion else self.game_board.engine_manager.engine
        settings = ""
        for v in engine.options.values():
            if v.name in ['UCI_Chess960', 'UCI_Variant', 'Ponder', 'MultiPV'] or v.type == 'button':
                continue
            cur_set = engine_cfg[v.name] if v.name in engine_cfg else v.default
            settings += f'<br><label for="{v.name}_id">{v.name}:</label>'
            match v.type:
                case 'check':
                    checked = "checked" if cur_set else ""
                    settings += f'<input id="{v.name}_id" name="{v.name}" type="checkbox" {checked}>'
                case 'spin':
                    size = max(len(str(v.min)), len(str(v.max)))+1
                    settings += f'<input id="{v.name}_id" name="{v.name}" type="number" min="{v.min}" max="{v.max}" value="{cur_set}" size="{size}">'
                case 'string':
                    settings += f'<input id="{v.name}_id" name="{v.name}" type="text" value="{cur_set}">'
                case 'combo':
                    settings += f'<select id="{v.name}_id" name="{v.name}">'
                    for o in v.var:
                        sel = 'selected' if o == v.default else ''
                        settings += f'<option value="{o}" {sel}>{o}</option>'
                    settings += '</select>'
        return text.replace('ENGINE_SETTINGS', settings)

    async def engine_settings_handler(self, request: web.BaseRequest):
        is_suggestion = "for" in request.query and request.query["for"] == "SUG"
        text = pathlib.Path(self.engine_settings).read_text()
        limit = self.game_board.engine_manager.limit_sug\
            if is_suggestion else self.game_board.engine_manager.limit
        time = str(limit.time)
        d = limit.depth
        depth = str(d) if d else '0'
        n = limit.nodes
        nodes = str(n) if n else '0'
        engine_cfg = self.game_board.options.sug_engine_cfg\
            if is_suggestion else self.game_board.options.engine_cfg
        title = 'Suggestion Engine' if is_suggestion else 'CPU Engine'
        text = text.replace('ENGINE_TITLE', title).replace(
            'ENGINE_SELECT', 'SUG' if is_suggestion else 'CPU').replace(
            'LIMIT_TIME', time).replace(
            'LIMIT_DEPTH', depth).replace(
            'LIMIT_NODES', nodes)
        text = await self.add_engine_settings(text, is_suggestion, engine_cfg)
        res = web.Response(text=text)
        res.content_type = 'text/html'
        return res

    async def set_engine_limit(self, request):
        # this is a POST request
        # ?time: int, ?depth: int, ?nodes: int, ?engine_select: [cpu, suggest]
        data = await request.post()
        time = float(data['time'])
        time = time if time > 0 else None
        depth = int(data['depth'])
        depth = depth if depth > 0 else None
        nodes = int(data['nodes'])
        nodes = nodes if nodes > 0 else None
        log.info(
            f'Setting time:{time}, depth:{depth}, nodes:{nodes} for {data["engine_select"]} from web')
        if not (time or depth or nodes):
            return web.Response(status=400, text='All Zeroes not allowed!')
        if data['engine_select'] == 'CPU':
            await self.game_board.engine_manager.set_engine_limit(time, depth, nodes)
        else:
            await self.game_board.engine_manager.set_sug_limit(time, depth, nodes)
        res = web.Response(status=303)
        return res

    async def set_engine_cfg(self, request: web.BaseRequest):
        # this is a POST request
        # str that is dict of cfg
        data = await request.post()
        sanitized = {}
        for key, value in data.items():
            if key not in ['UCI_Chess960', 'UCI_Variant', 'Ponder', 'MultiPV', 'engine_select']:
                sanitized[key] = value
        try:
            if data['engine_select'] == 'CPU':
                await self.game_board.engine_manager.set_engine_cfg(sanitized)
            else:
                await self.game_board.engine_manager.set_sug_engine_cfg(sanitized)
            log.info(f'Set {data["engine_select"]} engine with values: {sanitized}')
        except Exception as e:
            text = f'Exception {e}: {e.args}'
            log.error(text)
            return web.Response(status=400, text=text)

        return await self.engine_settings_handler(request)


async def start_server(board):
    app = web.Application()
    board_handlers = BoardAppHandlers(board)
    engine_handlers = EngineAppHandlers(board)
    app.router.add_route('GET', '/', board_handlers.index)
    app.router.add_route('GET', '/debug', board_handlers.debug_handler)
    app.router.add_route('GET', '/board.svg', board_handlers.board_svg_handler)
    app.router.add_route('GET', '/opening', board_handlers.opening_handler)
    app.router.add_route('GET', '/move_stack_frame',
                         board_handlers.move_stack_frame_handler)
    app.router.add_route('GET', '/move_stack',
                         board_handlers.move_stack_handler)
    app.router.add_route('GET', '/last_score',
                         board_handlers.last_score_handler)
    app.router.add_route('POST', '/read_board',
                         board_handlers.read_board_handler)
    app.router.add_route('POST', '/set_engine_limit',
                         engine_handlers.set_engine_limit)
    app.router.add_route('POST', '/set_engine_cfg',
                         engine_handlers.set_engine_cfg)
    app.router.add_route('GET', '/counter_openings_frame',
                         board_handlers.counter_openings_frame_handler)
    app.router.add_route('GET', '/counter_openings',
                         board_handlers.counter_openings_handler)
    app.router.add_route('GET', '/battery_status', board_handlers.get_battery)
    app.router.add_route('GET', '/engine_settings',
                         engine_handlers.engine_settings_handler)
    app.router.add_route('GET', '/timers', board_handlers.time_handler)
    app.router.add_route('GET', '/online_game',
                         board_handlers.online_game_handler)
    app.router.add_route('POST', '/start_online_challenge',
                         board_handlers.start_online_challenge_handler)
    app.router.add_route('POST', '/start_online_seek',
                         board_handlers.seek_game_handler)
    app.router.add_route('GET', '/online_chat',
                         board_handlers.online_chat_handler)
    app.router.add_route('GET', '/mystyle.css', board_handlers.css_handler)
    return app

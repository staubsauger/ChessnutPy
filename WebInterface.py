import ast
import pathlib
import json
import re

import chess.svg
import chess.engine
from aiohttp import web
import chess
import BoardGame
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
        self.game_board: BoardGame = board
        self.last_svg_board_fen = None
        self.last_svg_board = None
        self.last_opening = None
        self.css = './WebInterface_Helpers/mystyle.css'

    async def index(self, request):
        return web.FileResponse(self.index_template)

    async def css_handler(self, request):
        return web.FileResponse(self.css)

    async def engine_settings_handler(self, request):
        text = pathlib.Path(self.engine_settings).read_text()
        text = text.replace('LIMIT_TIME', str(
            self.game_board.engine_manager.limit.time))
        text = text.replace('ENGINE_SETTINGS', json.dumps(
            self.game_board.options.engine_cfg))
        res = web.Response(text=text)
        res.content_type = 'text/html'
        return res

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
        starting_board: chess.Board = self.game_board.board.copy()
        if len(starting_board.move_stack) == 0:
            return web.Response()
        while len(starting_board.move_stack) > 0:
            starting_board.pop()
        moves = starting_board.variation_san(data)
        bm = re.sub(r'\d+\.', r'<b>\g<0></b>', moves)
        res = web.Response(text=bm)
        return res

    async def last_score_handler(self, request):
        return web.json_response(self.game_board.last_score / 100 if self.game_board.last_score else None)

    async def read_board_handler(self, request):
        await self.game_board.exit_read_board_and_select_color()
        return web.Response(status=303)

    async def start_online_challenge_handler(self, request):
        await self.game_board.exit_read_board_and_select_color(wants_online='challenge')
        return await self.online_game_handler(request)

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

    async def online_chat_handler(self, request):
        text = self.game_board.lichess.game.chat if self.game_board.lichess and self.game_board.lichess.game else ''
        return web.Response(text=text)

    async def set_engine_cfg(self, request):
        # this is a POST request
        # str that is dict of cfg
        log.info(self.game_board.engine_manager.engine.config)
        data = await request.post()
        d = json.loads(data['cfg_dict'])
        sanitized = {}
        for key in d:
            if key not in ['UCI_Chess960', 'UCI_Variant', 'Ponder', 'MultiPV']:
                sanitized[key] = d[key]
        try:
            await self.game_board.engine_manager.set_engine_cfg(sanitized)
        except Exception as e:
            text = f'Exception {e}: {e.args}'
            log.error(text)
            return web.Response(status=400, text=text)
        return await self.engine_settings_handler(request)

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
        rated = True if rated == 'on' else False
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
            return f'<div title="weight: {entry.weight}" style="padding: -8px"> {f"{opening[0][0]}: {opening[0][1]}" if opening else "Unamed"} -> {entry.move.uci()} </div>'
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


async def start_server(board):
    app = web.Application()
    handlers = BoardAppHandlers(board)
    app.router.add_route('GET', '/', handlers.index)
    app.router.add_route('GET', '/debug', handlers.debug_handler)
    app.router.add_route('GET', '/board.svg', handlers.board_svg_handler)
    app.router.add_route('GET', '/opening', handlers.opening_handler)
    app.router.add_route('GET', '/move_stack_frame',
                         handlers.move_stack_frame_handler)
    app.router.add_route('GET', '/move_stack', handlers.move_stack_handler)
    app.router.add_route('GET', '/last_score', handlers.last_score_handler)
    app.router.add_route('POST', '/read_board', handlers.read_board_handler)
    app.router.add_route('POST', '/set_engine_limit',
                         handlers.set_engine_limit)
    app.router.add_route('POST', '/set_engine_cfg', handlers.set_engine_cfg)
    app.router.add_route('GET', '/counter_openings_frame',
                         handlers.counter_openings_frame_handler)
    app.router.add_route('GET', '/counter_openings',
                         handlers.counter_openings_handler)
    app.router.add_route('GET', '/battery_status', handlers.get_battery)
    app.router.add_route('GET', '/engine_settings',
                         handlers.engine_settings_handler)
    app.router.add_route('GET', '/timers', handlers.time_handler)
    app.router.add_route('GET', '/online_game', handlers.online_game_handler)
    app.router.add_route('POST', '/start_online_challenge',
                         handlers.start_online_challenge_handler)
    app.router.add_route('POST', '/start_online_seek',
                         handlers.seek_game_handler)
    app.router.add_route('GET', '/online_chat', handlers.online_chat_handler)
    app.router.add_route('GET', '/mystyle.css', handlers.css_handler)
    return app

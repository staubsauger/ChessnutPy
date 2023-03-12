import ast
import pathlib
import json

import chess.svg
import chess.engine
from aiohttp import web
import chess
import BoardGame


def svg_board(board, player_color):
    fill = {}
    if board.is_check():
        fill = {board.king(board.turn): 'red'}
    attackable = filter(lambda pos: board.piece_at(pos) and board.piece_at(pos).color == board.turn and
                                    board.is_attacked_by(not board.turn, pos),
                        chess.SQUARES)
    for square in attackable:
        fill[square] = 'yellow'
    return chess.svg.board(board, size=350, lastmove=board.move_stack[-1] if len(board.move_stack) > 0 else None,
                           fill=fill, flipped=not player_color)


class BoardAppHandlers:
    def __init__(self, board: BoardGame, index_template='test.html'):
        self.index_template = index_template
        self.game_board: BoardGame = board

    async def hello(self, request):
        text = pathlib.Path(self.index_template).read_text()
        text = text.replace("CUR_OPENING", str(self.game_board.game.print_openings(self.game_board.board)))
        b = map(lambda l: f'<p>{l}</p>\n', str(self.game_board.board).split('\n'))
        text = text.replace("BOARD_STATE", ' '.join(b))
        res = web.Response(text=text)
        res.content_type = 'text/html'
        return res

    async def debug_handler(self, request):
        data = {}
        for e in self.game_board.__dict__:
            data[str(e)] = str(self.game_board.__dict__[e]).strip('\n')
        res = web.json_response(data=data)
        return res

    async def board_svg_handler(self, request):
        text = svg_board(self.game_board.board, self.game_board.player_color)
        res = web.Response(text=text)
        res.content_type = 'image/svg+xml'
        return res

    async def opening_handler(self, request):
        data = self.game_board.game.print_openings(self.game_board.board)
        return web.json_response(data)

    async def move_stack_handler(self, request) -> web.Response:
        data = self.game_board.board.move_stack
        board = self.game_board.board.copy()
        while len(board.move_stack) > 0:
            board.pop()
        text = board.variation_san(data)
        return web.Response(text=text)

    async def last_score_handler(self, request):
        return web.json_response(self.game_board.last_score / 100 if self.game_board.last_score else None)

    async def read_board_handler(self, request):
        await self.game_board.exit_read_board_and_select_color()
        return web.Response(status=303)

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
        limit = chess.engine.Limit(time=time, depth=depth, nodes=nodes)
        print(f'Setting time:{time}, depth:{depth}, nodes:{nodes} for {data["engine_select"]} from web')
        if not (time or depth or nodes):
            return web.Response(status=400, text='All Zeroes not allowed!')
        if data['engine_select'] == 'CPU':
            self.game_board.game.limit = limit
        else:
            self.game_board.game.limit_sug = limit
        res = web.Response(status=303)
        return res

    async def set_engine_cfg(self, request):
        # this is a POST request
        # str that is dict of cfg
        data = await request.post()
        d = json.loads(data['cfg_dict'])
        sanitized = {}
        for key in d:
            if key not in ['UCI_Chess960', 'UCI_Variant', 'MultiPV', 'Ponder']:
                sanitized[key] = d[key]
        await self.game_board.game.engine.configure(sanitized)
        return web.Response(status=303)


async def start_server(board):
    app = web.Application()
    handlers = BoardAppHandlers(board)
    app.router.add_route('GET', '/', handlers.hello)
    app.router.add_route('GET', '/debug', handlers.debug_handler)
    app.router.add_route('GET', '/board.svg', handlers.board_svg_handler)
    app.router.add_route('GET', '/opening', handlers.opening_handler)
    app.router.add_route('GET', '/move_stack', handlers.move_stack_handler)
    app.router.add_route('GET', '/last_score', handlers.last_score_handler)
    app.router.add_route('POST', '/read_board', handlers.read_board_handler)
    app.router.add_route('POST', '/set_engine_limit', handlers.set_engine_limit)
    app.router.add_route('POST', '/set_engine_cfg', handlers.set_engine_cfg)
    return app

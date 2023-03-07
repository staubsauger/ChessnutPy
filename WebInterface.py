import pathlib

import chess.svg
from aiohttp import web
import chess
import BoardGame


def svg_board(board, player_color):
    fill = {}
    if board.is_check():
        fill = {board.king(board.turn): 'red'}
    return chess.svg.board(board, size=350, lastmove=board.move_stack[-1] if len(board.move_stack) > 0 else None,
                           fill=fill, flipped=not player_color)


class BoardAppHandlers:
    def __init__(self, board: BoardGame, index_template='test.html'):
        self.index_template = pathlib.Path(index_template).read_text()
        self.game_board: BoardGame = board

    async def hello(self, request):
        text = self.index_template
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
        board = chess.Board()
        text = board.variation_san(data)
        return web.Response(text=text)

    async def last_score_handler(self, request):
        return web.json_response(self.game_board.last_score/100 if self.game_board.last_score else None)


async def start_server(board):
    app = web.Application()
    handlers = BoardAppHandlers(board)
    app.router.add_route('GET', '/', handlers.hello)
    app.router.add_route('GET', '/debug', handlers.debug_handler)
    app.router.add_route('GET', '/board.svg', handlers.board_svg_handler)
    app.router.add_route('GET', '/opening', handlers.opening_handler)
    app.router.add_route('GET', '/move_stack', handlers.move_stack_handler)
    app.router.add_route('GET', '/last_score', handlers.last_score_handler)
    return app


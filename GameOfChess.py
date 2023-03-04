import chess
import chess.engine
import chess.polyglot
import asyncio


class GameOfChess:

    def __init__(self, engine_limit=chess.engine.Limit(time=0.1), suggestion_limit=chess.engine.Limit(time=1.5),
                 suggestion_book="/usr/share/scid/books/Elo2400.bin") -> None:
        self.engine = chess.engine.SimpleEngine.popen_uci("/home/rudi/Games/schach/texel-chess/texel/build/texel")
        self.engine_suggest = chess.engine.SimpleEngine.popen_uci("stockfish")
        self.suggestion_book = suggestion_book
        self.limit = engine_limit
        self.limit_sug = suggestion_limit
        self.engine.configure({'UCI_LimitStrength': True, 'UCI_Elo': 800, 'OwnBook': True})
        self.checkmate = False
        self.engines_running = True

    def getcpumove(self, board):
        cpumove = self.engine.play(board, self.limit)
        return cpumove.move

    def get_score(self, board):
        score = self.engine_suggest.analyse(board, self.limit_sug).get('score')
        return score.pov(True) # returns score in cp relative to white -> always

    def getmovesuggestion(self, board):
        move = self.getbookmove(board)
        if not move:
            print("Engine move")
            move = self.engine.play(board, self.limit_sug).move
        return f"{move}"  # ex "e3e4"

    def getbookmove(self, board):
        with chess.polyglot.open_reader(self.suggestion_book) as reader:
            try:
                move = reader.weighted_choice(board)
                print(move)
                return move.move
            except IndexError:
                return None
    def quitchess(self):
        self.engine.quit()

# board = chess.Board("rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b")
# c = GameOfChess()
# while not c.checkmate:
#     m = str(c.getcpumove(board))
#     print(m, type(m))
#     print(chess.Move.from_uci(m))
#     board.push_san(m)
#     print(board.is_checkmate)
#     if board.is_checkmate():
#         print("checkmate")
#         c.quitchess()
#         c.checkmate = True
#     else:
#         print("not checkmate,go on")
#     print(board)
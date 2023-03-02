import chess
import chess.engine
import asyncio


class GameOfChess:

    
    def __init__(self) -> None:
        self.engine = chess.engine.SimpleEngine.popen_uci("stockfish")
        self.limit = chess.engine.Limit(time=0.1, depth=1)
        self.checkmate = False

    def getcpumove(self, board):
        cpumove = self.engine.play(board, self.limit)
        return cpumove.move

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
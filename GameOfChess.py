import chess
import chess.engine
import asyncio


class GameOfChess:

    def __init__(self) -> None:
        self.engine = chess.engine.SimpleEngine.popen_uci("stockfish")
        self.limit = chess.engine.Limit(time=5.0)
        
    def getcpumove(self, board):
        cpumove = self.engine.play(board, self.limit)
        return cpumove.move

    def quitchess(self):
        self.engine.quit()

# print(chess.Board().fen())
# c = GameOfChess(chess.Board().fen())
# c.makemove("e2e4")
# print(c.board)
# print(c.getcpumove())
# c.quitchess()

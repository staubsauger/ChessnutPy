import chess

"""

Get a fen and generate all legal moves and their fens

"""
def getlegalfens(fen):
    legalfens = []
    board = chess.Board(fen)
    legalmoves = board.generate_legal_moves()
    for i in legalmoves:
        tempboard = chess.Board(fen)
        tempboard.push_san(str(i))
        legalfens.append(tempboard.fen().split()[0])
    return legalfens



"""
a python function which compares two chess fens and returns on which fields a piece is wrong
"""
import chess


def convert_fen(fen):
    # noinspection SpellCheckingInspection
    """
        convert "r1bqkbnr/pppppppp/2n5/8/2P5/8/PP1PPPPP/RNBQKBNR w KQkq c6 0 2"
        to "r1bqkbnr/pppppppp/11n11111/11111111/11P11111/11111111/PP1PPPPP/RNBQKBNR"
        """
    fen = fen.split()[0]
    new_fen = ""
    for piece in fen:
        new_fen += "1"*int(piece) if piece.isdigit() and piece != '1' else piece
    return new_fen


def compare_chess_fens(target_fen, cur_fen):
    # noinspection SpellCheckingInspection
    """
        takes target_fen and cur_fen and returns which pieces are wrong on fen2
        fen like "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        return like [['P','d4'],['1', d2']] -> '1' = empty field,  'letters' = piece
        """
    def row_as_num(x):
        return 8 - x

    col_as_letter = {0: "a", 1: "b", 2: "c", 3: "d", 4: "e", 5: "f", 6: "g", 7: "h"}
    target_rows = convert_fen(target_fen).split("/")
    cur_rows = convert_fen(cur_fen).split("/")
    differences = []
    row = 0
    for i in range(len(target_rows)):
        if target_rows[i] != cur_rows[i]:
            col = 0
            for b in range(len(cur_rows[i])):
                if target_rows[i][b] != cur_rows[i][b]:
                    pos = str(col_as_letter[col]) + str(row_as_num(row))
                    cur_piece = cur_rows[i][b]
                    target_piece = target_rows[i][b]
                    differences.append((cur_piece, pos, target_piece))
                col += 1
        row += 1
    return differences


def fen_diff_leds(fen_diff):
    """
    find all led pairs to fix the board
    [(chess.Piece('P'), chess.D4, None), (None, chess.D2, chess.Piece('P'), (chess.Piece('P'), chess.D5, None)] ->
    [chess.SquareSet(chess.D4, chess.D2), chess.SquareSet(chess.D5)]
    """
    fen_diff = fen_diff.copy()
    leds = []

    def find_pair(fd):
        for diff in fd:
            if start[2] == diff[0]:  # did we find a pair?
                leds.append(chess.SquareSet([diff[1], start[1]]))
                return diff
    while len(fen_diff) > 0:
        start = fen_diff.pop(0)
        if start[2] is None:
            new_start = None
            for d in fen_diff:
                if d[2] is not None:
                    fen_diff.append(start)
                    new_start = d
                    break
            if new_start:
                start = new_start
                fen_diff.remove(new_start)
        partner = find_pair(fen_diff)
        if partner:
            fen_diff.remove(partner)
        else:
            leds.append(chess.SquareSet([start[1]]))  # we never found a pair
    return leds

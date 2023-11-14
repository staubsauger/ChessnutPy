import hashlib
import os.path
import pathlib
import re
import chess
import chess.engine
import chess.polyglot
import chess.pgn
import chess.svg
import time
# noinspection PyUnresolvedReferences
import asyncio

import logging
log = logging.getLogger("ChessnutPy")


class EngineManager:

    def __init__(self, options) -> None:
        self.options = options
        self.engine_path = options.engine_cmd
        self.transport = None
        self.engine = None  # chess.engine.SimpleEngine.popen_uci(engine_path)
        self.suggestion_engine_path = options.engine_suggest_cmd
        self.transport_suggest = None
        # chess.engine.SimpleEngine.popen_uci(suggestion_engine_path)
        self.engine_suggest = None
        self.suggestion_book = options.suggestion_book_dir
        self.limit = chess.engine.Limit(time=options.engine_time, nodes=options.engine_nodes,
                                        depth=options.engine_depth)
        self.limit_sug = chess.engine.Limit(time=options.sug_time, nodes=options.sug_nodes,
                                            depth=options.sug_depth)
        self.engines_running = False
        self.eco_pgn = None  # chess.pgn.BoardGame()
        self.eco_dict = {}
        # self.init_scid_eco_file()
        self.eco_file = options.eco_file
        self.dict_cache_file = 'eco_dict.cache'
        self.last_suggestion = None
        self.last_ai_move = None
        self.username = options.username

        if options.eco_file and not (os.path.exists(self.dict_cache_file) and self.read_eco_dict()):
            self.init_scid_eco_dict()
            self.write_eco_dict()

    async def set_engine_limit(self, time, nodes, depth, at_init=False):
        self.limit = chess.engine.Limit(time, nodes, depth)
        self.options.engine_time = time
        self.options.engine_nodes = nodes
        self.options.engine_depth = depth
        if not at_init:
            self.options.save_function()

    async def set_engine_cfg(self, cfg):
        self.options.engine_cfg = cfg
        await self.engine.configure(cfg)
        self.options.save_function()

    async def set_sug_limit(self, time, nodes, depth, at_init=False):
        self.limit_sug = chess.engine.Limit(time, nodes, depth)
        self.options.sug_time = time
        self.options.sug_nodes = nodes
        self.options.sug_depth = depth
        if not at_init:
            self.options.save_function()

    async def set_sug_engine_cfg(self, cfg):
        self.options.sug_engine_cfg = cfg
        await self.engine_suggest.configure(cfg)
        self.options.save_function()

    async def init_engines(self):
        self.transport, self.engine =\
            await chess.engine.popen_uci(self.engine_path)
        self.transport_suggest, self.engine_suggest =\
            await chess.engine.popen_uci(self.suggestion_engine_path)
        await self.engine.configure(self.options.engine_cfg)
        await self.engine_suggest.configure(self.options.sug_engine_cfg)
        self.engines_running = True

    async def get_cpu_move(self, board):
        if self.options.engine_use_ext_book:
            log.info("using external opening book.")
            bookmove = self.get_book_move(
                board, self.options.engine_ext_book_dir, weighted=False)
            if bookmove:
                log.info("Engine takes move out of book.")
                return bookmove
        log.info("No opening found, engine plays on its own")
        try:
            self.last_ai_move = await self.engine.play(board, self.limit)
            return self.last_ai_move.move
        except asyncio.CancelledError:
            log.error("AI move stopped.\nThis should never happen.")

    async def get_score(self, board):
        score = (await self.engine_suggest.analyse(board, self.limit_sug)).get('score')
        # returns score in cp relative to white -> always
        return score.pov(True)

    async def get_move_suggestion(self, board, min_time=0.0):
        try:
            start_time = time.time()
            move = self.get_book_move(board, self.suggestion_book)
            play = None
            if not move:
                log.info("Engine move: ")
                play = await self.engine_suggest.play(board, self.limit_sug)
                move = play.move
                log.info(move)
            if min_time == 0.0:
                self.last_suggestion = play if play else move
            time_spend = time.time() - start_time
            if time_spend < min_time:
                await asyncio.sleep(min_time-time_spend)
            return move
        except asyncio.exceptions.CancelledError:
            log.info("suggestion was canceled")

    def get_book_move(self, board, book, weighted=True):
        with chess.polyglot.open_reader(book) as reader:
            try:
                move = reader.weighted_choice(
                    board) if weighted else reader.choice(board)
                log.info(move)
                return move.move
            except IndexError:
                return None

    def get_book_moves(self, board):
        with chess.polyglot.open_reader(self.suggestion_book) as reader:
            try:
                # we cant return the interator directly since we close the file after returning
                return [e for e in reader.find_all(board)]
            except IndexError:
                return None

    def print_openings(self, board):
        if self.eco_pgn:
            cur_var = self.eco_pgn
            for n in board.move_stack:
                if cur_var.has_variation(n):
                    cur_var = cur_var.variation(n)
                else:
                    cur_var = None
                    break
            if cur_var:
                return '\n'.join(reversed(cur_var.comment.split('\n')))
            else:
                return f'no openers found: {" ".join(map(lambda m: m.uci(), board.move_stack))}'
        else:
            fen = board.board_fen()
            try:
                return self.eco_dict[fen]
            except KeyError:
                return None

    async def quit_chess_engines(self):
        if self.engines_running:
            await self.engine.quit()
            await self.engine_suggest.quit()
            self.engines_running = False

    def write_to_pgn(self, board):
        # check if we have a full movestack
        temp_board = board.board.copy()
        for i in range(len(temp_board.move_stack)):
            temp_board.pop()
        if temp_board.fen() != chess.Board().fen():
            return
        cur_time = time.localtime()
        day_str = f'{cur_time.tm_year}.{cur_time.tm_mon:02}.{cur_time.tm_mday:02}'
        time_str = f"{day_str}_{cur_time.tm_hour}_{cur_time.tm_min}"
        game = chess.pgn.Game()
        # noinspection SpellCheckingInspection
        game.headers["Event"] = "VakantOS"
        game.headers["Date"] = day_str
        if board.player_color:
            game.headers["White"] = self.username  # os.getlogin()
            game.headers["Black"] = str(self.engine.id["name"])
        else:
            game.headers["Black"] = self.username  # os.getlogin()
            game.headers["White"] = str(self.engine.id["name"])
        res = board.board.result()
        if res == '*':
            if board.winner == chess.WHITE:
                res = '1-0'
            elif board.winner == chess.BLACK:
                res = '0-1'
            else:
                res = '1/2-1/2'
        game.headers["Result"] = res
        if len(board.board.move_stack) == 0:
            log.info("No PGN Written")
            return
        move = board.board.move_stack.pop(0)
        node = game.add_main_variation(move)
        for move in board.board.move_stack:
            node = node.add_main_variation(move)
        print(game, file=open(f"{time_str}.pgn", 'w'))
        log.info("PGN written")

    def init_eco_file(self, ):
        """
        read the eco file with format:
        'E94    1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5 7. O-O "King's Indian, Classical Variation"'
        and fill self.eco_pgn with the moves and names
        """
        with open(self.eco_file, "rt") as eco_file:
            eco_line = eco_file.readline().strip()
            while eco_line:
                split = eco_line.split('"')
                name = split[1] if len(split) > 1 else ""
                rest = split[0]
                split = rest.split(' ')
                code = split[0]
                moves = list(filter(lambda m: len(
                    m) > 1 and '.' not in m, split[1:]))
                b = chess.Board()
                id_string = f'({name}, {code})\n'
                uci_moves = list(map(lambda m: b.push_san(m.strip()), moves))
                self.move_list_to_pgn(id_string, uci_moves)
                eco_line = eco_file.readline()

    def init_scid_eco_both(self):
        self.eco_pgn = chess.pgn.Game()
        with open(self.eco_file, "rt") as eco_file:
            for name, code, uci_moves, board in read_scid_eco_entries(eco_file):
                self.move_list_to_pgn(f'({name}, {code})\n', uci_moves)
                fen = board.board_fen()
                try:
                    self.eco_dict[fen].append((name, code))
                except KeyError:
                    self.eco_dict[fen] = [(name, code)]

    def init_scid_eco_file(self):
        """
        read the eco file with format:
        'A03 "Bird: 1...d5 2.Nf3 Nf6 3.g3 g6: 5.d3"
            1.f4 d5 2.Nf3 Nf6 3.g3 g6 4.Bg2 Bg7 5.d3 *' -> ["1", "f4 d5 2", "Nf3 Nf6 3", ...]
        and fill self.eco_pgn with the moves and names
        """
        self.eco_pgn = chess.pgn.Game()
        with open(self.eco_file, "rt") as eco_file:
            for name, code, uci_moves in read_scid_eco_entries(eco_file):
                self.move_list_to_pgn(f'({name}, {code})\n', uci_moves)

    def init_scid_eco_dict(self):
        with open(self.eco_file, 'r') as eco_file:
            duplicates = 0
            for name, code, moves, board in read_scid_eco_entries(eco_file):
                fen = board.board_fen()
                try:
                    self.eco_dict[fen].append((name, code))
                    duplicates += 1
                except KeyError:
                    self.eco_dict[fen] = [(name, code)]
            log.info(f'duplicates: {duplicates}')

    def move_list_to_pgn(self, id_string, uci_moves):
        cur_var = self.eco_pgn
        if len(uci_moves) < 1:
            cur_var.comment += id_string
        for i, cur_move in enumerate(uci_moves):
            if cur_var.has_variation(cur_move):
                if id_string not in cur_var.variation(cur_move).comment:
                    # if this is the last move: put id on the front of the string
                    if len(uci_moves) == i + 1:
                        cur_var.variation(cur_move).comment = \
                            f'{id_string}\n{cur_var.variation(cur_move).comment}'
                    else:
                        cur_var.variation(cur_move).comment += id_string

            else:
                cur_var.add_variation(cur_move).comment = id_string
            cur_var = cur_var.variation(cur_move)

    def write_eco_dict(self):
        with open("eco_dict.cache", 'w') as f:
            h = hashlib.md5(pathlib.Path(
                self.eco_file).read_bytes()).hexdigest()
            print(h, file=f)
            for key in self.eco_dict:
                val = self.eco_dict[key]
                print(f'{key}|{val[0][1]}|{val[0][0]}', file=f)
        log.info('wrote eco_dict')

    def read_eco_dict(self):
        with open(self.dict_cache_file, 'r') as f:
            h = str(hashlib.md5(pathlib.Path(
                self.eco_file).read_bytes()).hexdigest())
            nh = f.readline().strip()
            if h != nh:
                log.info(f'hashes didnt match:\n{h}\n{nh}')
                return False
            for line in f:
                fen, name, code = line.strip(' \n').split('|')
                self.eco_dict[fen] = [(name, code)]
        log.info('read eco_dict')
        return True


def read_scid_eco_entries(eco_file):
    count = 0

    def read_line():
        nonlocal count
        count += 1
        return eco_file.readline().strip(' \n')

    eco_line = read_line()
    while eco_line:
        # lines gathered right before the while check cant already be stripped, or we will endless loop
        eco_line = eco_line.strip(' \n')  # so we strip them here
        while eco_line.startswith("#"):
            eco_line = read_line()
        while len(eco_line) == 0 or eco_line[-1] != '*':
            eco_line += ' ' + read_line()
        split = eco_line.split('"')
        code = split[0].strip()
        name = split[1] if len(split) > 1 else ""
        rest = split[2]
        split = rest.split('.')
        turns = map(lambda m: m[:-2].split(),
                    filter(lambda m: len(m.strip()) > 1, split))
        moves = []
        for t in turns:
            m1 = t[0]
            moves.append(m1)
            if len(t) > 1:
                m2 = t[1]
                moves.append(m2)
        b = chess.Board()
        uci_moves = list(map(lambda m: b.push_san(m.strip()), moves))
        yield name, code, uci_moves, b
        count += 1
        eco_line = eco_file.readline()
    log.info(count)


def read_uci_file(file_path):
    """Read a .uci file in the style of picochess to get uci setting presets for engines"""
    contents = ""
    with open(file_path) as file:
        contents = file.read()
    levels = {}
    pattern = re.compile('\[.*\][^[]*')
    for m in pattern.finditer(contents):
        lines = m.group().strip().splitlines()
        cfg = {}
        for l in lines[1:]:
            n, v = l.split('=', 2)
            cfg[n.strip()] = v.strip()
        levels[lines[0].strip('[]')] = cfg
    return levels

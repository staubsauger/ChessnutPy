import asyncio
import math

import chess

import animations
from ChessnutAir import ChessnutAir, loc_to_pos
from GameOfChess import GameOfChess
from constants import convertDict
from data2fen import convert_to_fen, pieces_from_data
from fencompare import compare_chess_fens, fen_diff_leds


class BoardGame(ChessnutAir):
    def __init__(self, board_fen=None, turn="w", castle="KQkq",
                 player_color=None, read_board=False, no_help=False, show_valid_moves=True, play_animations=True,
                 suggestion_book_dir="", engine_dir="", engine_suggest_dir="", eco_file=None):
        ChessnutAir.__init__(self)
        self.no_help = no_help
        self.should_read = read_board
        self.target_move = None
        self.move_end = None
        self.move_start = []
        self.running = False
        self.tick = False
        self.castling = False
        self.player_color_select = False
        self.to_blink = []
        self.to_light = []
        self.player_color = player_color
        self.board = chess.Board(f"{board_fen} {turn} {castle} - 0 1") if board_fen else chess.Board()
        self.target_fen = ""
        self.undo_loop = False
        self.player_turn = False
        self.game = GameOfChess(engine_dir, engine_suggest_dir, suggestion_book_path=suggestion_book_dir,
                                eco_file=eco_file)
        self.more_games = True
        self.winner = None
        self.inited = False
        self.cur_fen = " "
        self.show_valid = show_valid_moves
        self.is_check = False
        self.play_animations = play_animations
        self.fixing_board = False
        self.overrode_ai = False
        self.last_score = None

    def setup(self):
        self.target_move = None
        self.move_end = None
        self.move_start = []
        self.running = False
        self.tick = False
        self.castling = False
        self.player_color_select = False
        self.to_blink = []
        self.to_light = []
        self.player_color = None
        self.board = chess.Board()
        self.target_fen = ""
        self.undo_loop = False
        self.player_turn = False
        self.winner = None
        self.inited = False
        self.is_check = False
        self.overrode_ai = False
        self.last_score = None

    def board_state_as_fen(self):
        self.cur_fen = convert_to_fen(self.board_state)
        return self.cur_fen

    async def suggest_move(self, move, blink=False):
        if self.no_help:
            return
        move = move[:4]
        leds = [move[2:], move[:2]]
        if blink:
            self.to_blink = leds
        else:
            self.to_light = leds
            self.to_blink = []

    async def led_score(self, score=None):
        # check if score exists, else await score
        score = score if score else int((await self.game.get_score(self.board)).score())
        print(score)
        self.last_score = score
        # Max score is divided into increments via half of the LED matrix.
        # I.e. if leds has 8 entries, increments = 200/ 4 = 50
        # if leds has 64 entires, increments = 1000/32 = 31.25
        #                                    =  320/32 = 10
        leds = ['a4', 'a3', 'a2', 'a1', 'b1', 'b2', 'b3', 'b4', 'c4', 'c3', 'c2', 'c1', 'd1', 'd2', 'd3', 'd4',
                'e4', 'e3', 'e2', 'e1', 'f1', 'f2', 'f3', 'f4', 'g4', 'g3', 'g2', 'g1', 'h1', 'h2', 'h3', 'h4',
                'h5', 'h6', 'h7', 'h8', 'g8', 'g7', 'g6', 'g5', 'f5', 'f6', 'f7', 'f8', 'e8', 'e7', 'e6', 'e5',
                'd5', 'd6', 'd7', 'd8', 'c8', 'c7', 'c6', 'c5', 'b5', 'b6', 'b7', 'b8', 'a8', 'a7', 'a6', 'a5']
        max_score = 320
        increments = (max_score*2)/len(leds)
        # return the score relative to the increments that we just created
        score_in_increments = int(math.ceil(score/increments))  # ceiling to only have 0 leds at score = 0
        # make sure we are within -len(leds)/2<score_in_increments<len(leds)/2
        score_in_increments = max(min(score_in_increments, len(leds)//2), -len(leds)//2)
        # define the LEDs we need to light for this move, and light them!
        start = 0 if score_in_increments >= 0 else score_in_increments
        end = score_in_increments if score_in_increments >= 0 else len(leds)
        self.to_blink = leds[start:end]
        await self.change_leds(self.to_blink)
        await asyncio.sleep(1.5)
        await self.blink_tick()

    async def player_king_hover_action(self):  # -> get book move first and then analyses engine output
        if self.player_color_select:
            print("Selected White")
            self.player_color = chess.WHITE
            self.player_color_select = False
        else:
            await self.blink_tick()
            print("suggesting move: ", end='')
            move = await self.game.get_move_suggestion(self.board)
            print(move)
            self.to_blink = self.to_light = []
            await self.suggest_move(move)
            self.move_end = None
            self.move_start = []

    async def cpu_king_hover_action(self):
        if self.player_color_select:
            print("Selected Black")
            self.player_color = chess.BLACK
            self.player_color_select = False
        else:
            print("LED Score")
            await self.led_score()

    async def piece_down(self, location, piece_id):
        #  todo: handle player pushing pieces instead of lifting them (up and down event are reversed)
        async def king_hover_action():
            if (self.player_color == chess.WHITE and p_str == 'K')\
                    or (self.player_color == chess.BLACK and p_str == 'k'):
                await self.player_king_hover_action()
            elif p_str == 'K' or p_str == 'k':
                await self.cpu_king_hover_action()
        pos = loc_to_pos(location)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} down")
        if self.player_turn and len(self.move_start) > 0 and not self.fixing_board:
            self.to_light = []
            ms = await self.find_start_move()
            self.to_blink = []
            if ms and ms != pos:
                self.move_end = (pos, p_str)
            else:
                p_moves = list(filter(lambda m: m[1] == 'K' or m[1] == 'k', self.move_start))
                if len(p_moves) > 0:
                    ms = p_moves[0][0]
                    if ms == pos:
                        await king_hover_action()
                self.move_end = (pos, p_str)
            if not ms and len(self.board.move_stack) > 0:
                undo_move = f'{self.board.move_stack[-1]}'
                if any(filter(lambda p: p[0] == undo_move[2:], self.move_start)):
                    self.move_end = (pos, p_str)
            if self.player_color_select:
                self.move_start = []
                self.to_blink = ['e1', 'e8']

    async def piece_up(self, location, piece_id):
        pos = loc_to_pos(location)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} up")
        self.to_light.append(pos)
        self.move_end = None
        self.move_start.append((pos, p_str))
        if not self.fixing_board:
            self.to_blink = []
            if self.show_valid:
                for move in self.board.legal_moves:
                    m_str = f"{move}"
                    from_square = m_str[:2]
                    to_square = m_str[2:]
                    if from_square == pos:
                        self.to_blink.append(to_square)
                    elif to_square == pos:
                        self.to_blink.append(from_square)
            if len(self.board.move_stack) > 0:
                undo = f"{self.board.peek()}"
                if undo[2:] == pos:
                    self.to_blink.append(undo[:2])

    def check_and_display_check(self):
        if self.is_check:
            # find king in check
            square = filter(lambda p: p[1] == 'k' or p[1] == 'K',
                            enumerate(map(lambda p: convertDict[p],
                                      pieces_from_data(self.board_state))))
            if self.board.turn == chess.WHITE:
                square = filter(lambda p: p[1] == 'K', square)
            else:
                square = filter(lambda p: p[1] == 'k', square)
            square = list(square)
            if len(square) > 0:
                pos = loc_to_pos(square[0][0])
                self.to_blink = [pos]

    async def blink_tick(self, sleep_time=0.0):
        self.tick = not self.tick
        if self.tick:
            await self.change_leds(self.to_blink+self.to_light)
        else:
            await self.change_leds(self.to_light)
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)

    async def check_quit(self) -> bool:
        """
        Check if game should end because the kings were placed in the middle in specific ways
        if both kings are on black: black wins
        if both kings are on white: white wins
        if mixed and vertical: draw
        if mixed and horizontal: quit completely
        """
        def filter_fun(i):
            i = i[0]
            x = i % 8
            y = i // 8
            return 3 <= x <= 4 and 3 <= y <= 4  # -> four squares in the center
        relevant_positions = filter(filter_fun, enumerate(pieces_from_data(self.board_state)))  # should always be 4
        d5, e5, d4, e4 = map(lambda pos: convertDict[pos[1]] == 'k' or convertDict[pos[1]] == 'K', relevant_positions)
        if d5 and e4:  # both on white
            self.winner = chess.WHITE
            return True
        elif d4 and e5:  # both on black
            self.winner = chess.BLACK
            return True
        elif (e4 and e5) or (d4 and d5):  # Draw
            return True
        elif (e4 and d4) or (e5 and d5):  # we want to quit completely
            self.more_games = False  # maybe quit() here?
            return True
        return False

    async def fix_board(self, task=None):
        diffs = compare_chess_fens(self.board.fen(), self.board_state_as_fen())
        self.to_blink = self.to_light = []  # turn off any lights that might still be on
        if self.undo_loop and len(diffs) == 0:
            self.undo_loop = False
            self.overrode_ai = False
        if diffs:
            self.fixing_board = True
            print("board incorrect!\nplease fix")
            suggested = False
            while diffs:
                # check if we want to override an AI move
                if self.undo_loop and len(diffs) == 2:
                    move1 = chess.Move.from_uci(diffs[0][1]+diffs[1][1])
                    move2 = chess.Move.from_uci(diffs[1][1]+diffs[0][1])
                    if move1 in self.board.legal_moves:
                        self.board.push(move1)
                        self.overrode_ai = True
                        break
                    elif move2 in self.board.legal_moves:
                        self.board.push(move2)
                        self.overrode_ai = True
                        break
                # check if we want to quit/reset the game
                self.winner = None
                want_to_quit = await self.check_quit()
                if self.inited and want_to_quit:
                    self.running = False
                    return
                # Calculate LEDs needed to fix all diffs
                led_pairs = fen_diff_leds(diffs)
                to_display = led_pairs[0]  # generally only display LEDs to fix 1 diff
                if len(to_display) == 1:        # if only 1 LED needed
                    self.to_blink = to_display  # blink LED instead of lighting it
                    self.to_light = []
                else:
                    if not suggested:
                        self.to_blink = []
                    if self.castling and len(led_pairs) > 1:
                        # if the AI is doing a castling move we want to display the King pair
                        # if no king move exists display any pair
                        for p in led_pairs:
                            if p[0].startswith("e"):
                                to_display = p
                                break
                    self.to_light = to_display
                # check if the background task is done, if it is display results
                if not suggested and task and task.done():
                    would_have_done = task.result()
                    await self.suggest_move(would_have_done, blink=True)
                    suggested = True
                # actually change LEDs to light or blink and sleep a little
                await self.blink_tick(sleep_time=0.3)
                # todo: figure out if we should handle blinking in ChessnutAit so it happens while we await changes
                # await self.board_has_changed()
                diffs = compare_chess_fens(self.board.fen(), self.board_state_as_fen())
            print(f"board fixed!\n{self.board.fen()}")
            self.fixing_board = False
            if task and not task.done():
                task.cancel()
            await asyncio.sleep(0.2)
        else:
            test = self.board_state_as_fen()
            print(f"board correct:\n{chess.Board(test)}")
        # Move is Fixed
        self.castling = False
        self.to_light = self.to_blink = []
        if self.undo_loop and len(self.board.move_stack) > 0:
            next_undo = f"{self.board.peek()}"
            self.to_light = [next_undo[:2], next_undo[2:]]
        self.move_start = []
        self.move_end = None

    async def ai_move(self):
        has_player_move = len(self.board.move_stack) > 0
        would_have_done_task = None
        if has_player_move:
            player_move = self.board.pop()
            would_have_done_task = asyncio.create_task(self.game.get_move_suggestion(self.board.copy(), min_time=5.0))
            self.board.push(player_move)
        ai_play = await self.game.get_cpu_move(self.board)
        raw_move = ai_play.move
        move = f"{raw_move}"[:4]
        print("generating Move!", move)
        if self.board.is_castling(raw_move):
            self.castling = True
        self.board.push_uci(move)
        await self.fix_board(task=would_have_done_task)
        self.player_turn = True

    async def find_start_move(self):
        # find a move_start that has legal moves
        for legal_move in self.board.legal_moves:
            for pos, _ in self.move_start:
                if f"{legal_move}".startswith(pos):
                    return pos
        return None

    async def player_move(self):
        start_move = await self.find_start_move()
        if not start_move and len(self.move_start) > 0:
            start_move = self.move_start[0][0]
        if start_move \
                and self.move_end \
                and start_move != self.move_end[0]:
            move = start_move + self.move_end[0]
            if self.player_turn:
                moves = list(map(lambda m: f'{m}', filter(lambda m: f"{m}".startswith(move), self.board.legal_moves)))
                if len(moves) > 1:  # more than 1 move is legal -> promotion move
                    # we have to figure out the new piece
                    move += self.move_end[1].lower()
                if not await self.player_move_is_valid(move):
                    if not await self.want_to_undo(move):
                        print(f"illegal move {move}\n{self.board}")
                    await self.fix_board()
            self.move_start = []
            self.move_end = None

    async def player_move_is_valid(self, move):
        if self.board.is_legal(chess.Move.from_uci(move)):
            self.board.push_uci(move)
            print(self.board)
            print("Move-stack: ", list(map(lambda m: f'{m}', self.board.move_stack)))
            print("Player move: ", move)
            self.to_blink = self.to_light = []
            self.player_turn = self.board.turn == self.player_color
            self.overrode_ai = False
            self.undo_loop = False
            return True
        return False

    async def want_to_undo(self, move):
        if len(self.board.move_stack) > 0 and move[2:] + move[:2] == f"{self.board.peek()}":
            print("undoing moves!")
            self.board.pop()
            if len(self.board.move_stack) < 1:
                self.to_light = self.to_blink = []
                if self.board.turn != self.player_color:
                    await self.ai_move()
                self.move_start = []
            else:
                self.board.pop()
            self.undo_loop = True
            return True
        return False

    async def game_loop(self):
        await self.game.init_engines()
        if self.play_animations:
            await self.play_animation(animations.start_anim)
        else:
            await asyncio.sleep(1)  # wait for board to settle
        self.winner = None
        await self.maybe_read_board()
        self.inited = True
        await self.select_player_color()
        self.player_turn = self.board.turn == self.player_color
        await self.fix_board()
        self.to_blink = self.to_light = []
        if self.play_animations:
            await self.play_animation(animations.game_start_amin, sleep_time=0.1)
        self.running = True
        # all initializing is done to loop can finally begin
        while self.running:
            self.is_check = self.board.is_check()
            if self.board.is_checkmate():
                await self.play_animation(animations.check_mate_anim)
                print("checkmate!")
                self.running = False
                self.winner = not self.board.turn
                continue
            elif self.board.is_stalemate():
                await self.play_animation(animations.stalemate_anim)
                # noinspection SpellCheckingInspection
                print("Remis!")
                self.running = False
            if self.player_turn:
                self.check_and_display_check()
                await self.player_move()
            else:
                print(self.game.print_openings(self.board))
                await self.ai_move()
                print(self.game.print_openings(self.board))
            await self.blink_tick(sleep_time=0.3)
        print(f'winner was {self.winner}!')
        # save PGN here
        self.game.write_to_pgn(self)
        if self.more_games:
            # reset this object and call game_loop again
            self.setup()
            await self.game_loop()
        await self.game.quit_chess_engines()

    async def maybe_read_board(self):
        if self.should_read:
            self.board = chess.Board(f'{self.board_state_as_fen()} {"w" if self.player_color == chess.WHITE else "b"}')
            print(f'Read board state:\n{self.board}')
            self.should_read = False
        else:
            print("Board settled")
            await self.fix_board()

    async def select_player_color(self):
        if self.player_color is None:
            self.player_color = chess.WHITE
            self.player_turn = True
            self.player_color_select = True
            print('select a color by picking up a king')
            if self.play_animations:
                await self.play_animation(animations.pick_anim, sleep_time=0.4)
            self.to_blink = ["e8", "e1"]
        while self.player_color_select:
            await self.blink_tick(sleep_time=0.5)

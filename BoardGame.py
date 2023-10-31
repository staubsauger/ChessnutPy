import asyncio
import math
import typing

import chess
import chess.engine

import LiChess
import BoardGame_Helpers.animations as animations
from ChessnutAir import ChessnutAir, board_state_as_square_and_piece
from EngineManager import EngineManager
from BoardGame_Helpers.fencompare import fen_diff_leds

import logging
log = logging.getLogger("ChessnutPy")



class BoardGame(ChessnutAir):
    def __init__(self, options, player_color=None, no_suggestions=False):
        ChessnutAir.__init__(self)
        self.options = options
        self.no_suggestions = no_suggestions
        self.should_read = False
        self.target_move = None
        self.move_end = None
        self.move_start = []
        self.running = False
        self.castling = False
        self.player_color_select = False
        self.player_color = player_color
        self.board = chess.Board()
        self.target_fen = ""
        self.undo_loop = False
        self.player_turn = False
        self.engine_manager = EngineManager(options)
        self.more_games = True
        self.winner = None
        self.inited = False
        self.is_check = False
        self.fixing_board = False
        self.last_score = None
        self.maybe_read = False
        self.skip_pgn = False
        self.force_quit = True
        self.have_read_board = False
        self.init_lichess()
        self.is_online_game = False
        self.next_game_online = None
        self.online_seek_info = None

    def init_lichess(self):
        self.lichess = LiChess.LiChess(self.options.lichess_token) if self.options.lichess_token != '' else None

    def setup(self):
        log.info("in setup")
        self.target_move = None
        self.move_end = None
        self.move_start = []
        self.running = False
        self.tick = False
        self.castling = False
        self.player_color_select = False
        self.to_blink.clear()
        self.to_light.clear()
        self.player_color = None
        self.board = chess.Board()
        self.target_fen = ""
        self.undo_loop = False
        self.player_turn = False
        self.winner = None
        self.inited = False
        self.is_check = False
        self.last_score = None
        self.skip_pgn = False
        self.force_quit = True
        self.have_read_board = False
        self.is_online_game = self.next_game_online is not None

    async def suggest_move(self, move: chess.Move, blink=False):
        if self.no_suggestions or self.is_online_game:
            return
        leds = chess.SquareSet([move.from_square, move.to_square])
        if blink:
            self.to_blink = leds
        else:
            self.to_light = leds
            self.to_blink.clear()

    async def led_score(self, score=None):
        if self.is_online_game:
            return
        # check if score exists, else await score
        score = score if score else int((await self.engine_manager.get_score(self.board)).score())
        log.info(f"Score: {score}")
        self.last_score = score
        # Max score is divided into increments via half of the LED matrix.
        # I.e. if leds has 8 entries, increments = 200/ 4 = 50
        # if leds has 64 entries, increments = 1000/32 = 31.25
        #                                    =  320/32 = 10
        leds = ['a4', 'a3', 'a2', 'a1', 'b1', 'b2', 'b3', 'b4', 'c4', 'c3', 'c2', 'c1', 'd1', 'd2', 'd3', 'd4',
                'e4', 'e3', 'e2', 'e1', 'f1', 'f2', 'f3', 'f4', 'g4', 'g3', 'g2', 'g1', 'h1', 'h2', 'h3', 'h4',
                'h5', 'h6', 'h7', 'h8', 'g8', 'g7', 'g6', 'g5', 'f5', 'f6', 'f7', 'f8', 'e8', 'e7', 'e6', 'e5',
                'd5', 'd6', 'd7', 'd8', 'c8', 'c7', 'c6', 'c5', 'b5', 'b6', 'b7', 'b8', 'a8', 'a7', 'a6', 'a5']
        max_score = 320
        increments = (max_score * 2) / len(leds)
        # return the score relative to the increments that we just created
        score_in_increments = int(math.ceil(score / increments))  # ceiling to only have 0 leds at score = 0
        # make sure we are within -len(leds)/2<score_in_increments<len(leds)/2
        score_in_increments = max(min(score_in_increments, len(leds) // 2), -len(leds) // 2)
        # define the LEDs we need to light for this move, and light them!
        start = 0 if score_in_increments >= 0 else score_in_increments
        end = score_in_increments if score_in_increments >= 0 else len(leds)
        self.to_blink = chess.SquareSet(map(lambda p: chess.parse_square(p), leds[start:end]))

    async def player_king_hover_action(self):  # -> get book move first and then analyses engine output
        if self.player_color_select:
            log.info("Selected White")
            self.player_color = chess.WHITE
            self.player_color_select = False
            if self.maybe_read:
                self.should_read = True
                await self.maybe_read_board()
                self.maybe_read = False
        else:
            await self.blink_tick()
            log.info("suggesting move: ")
            move = await self.engine_manager.get_move_suggestion(self.board)
            self.to_blink.clear()
            self.to_light.clear()
            if move is not None:
                log.info(move)
                await self.suggest_move(move)
            self.move_end = None
            self.move_start = []

    async def cpu_king_hover_action(self):
        if self.player_color_select:
            log.info("Selected Black")
            self.player_color = chess.BLACK
            self.player_color_select = False
            if self.maybe_read:
                self.should_read = True
                await self.maybe_read_board()
                self.maybe_read = False
        else:
            log.info("LED Score")
            await self.led_score()

    async def piece_down(self, square: chess.Square, piece: chess.Piece):
        async def king_hover_action():
            if piece.piece_type == chess.KING:
                if self.player_color == piece.color:
                    await self.player_king_hover_action()
                else:
                    await self.cpu_king_hover_action()
        log.info(f"piece: {piece.symbol()} at {chess.square_name(square)} ({square}) down (move_start: {self.move_start})")
        if self.options.dragging_detection and len(self.move_start) == 0 and not self.fixing_board:
            self.move_end = (square, piece)
            return
        if self.player_turn and len(self.move_start) > 0 and not self.fixing_board:
            self.to_light.clear()
            ms = await self.find_start_move()
            log.info(f"ms: {ms}")
            self.to_blink.clear()
            if ms != None and ms != square:
                self.move_end = (square, piece)
                log.info(f"move_end: {self.move_end}")
            else:
                p_moves = list(filter(lambda m: m[1].piece_type == chess.KING, self.move_start))
                if len(p_moves) > 0:
                    ms = p_moves[0][0]
                    if ms == square:
                        await king_hover_action()
                self.move_end = (square, piece)
            if ms == None and len(self.board.move_stack) > 0:
                undo_move = self.board.peek()
                if any(filter(lambda p: p[0] == undo_move.to_square, self.move_start)):
                    self.move_end = (square, piece)
            if self.player_color_select:
                self.move_start = []
                self.to_blink = chess.SquareSet(self.find_king_squares())

    async def piece_up(self, square: chess.Square, piece: chess.Piece):
        log.info(f"piece: {piece.symbol()} at {chess.square_name(square)} up")
        self.to_light.add(square)
        if not self.options.dragging_detection:
            self.move_end = None
        self.move_start.append((square, piece))
        if not self.fixing_board:
            self.to_blink.clear()
            if self.options.show_valid_moves:
                for move in self.board.legal_moves:
                    if move.from_square == square:
                        self.to_blink.add(square)
                    elif move.to_square == square:
                        self.to_blink.add(square)
            if len(self.board.move_stack) > 0:
                undo = self.board.peek()
                if undo.to_square == square:
                    self.to_blink.add(undo.from_square)

    async def button_pressed(self, button):
        log.info(f'Button {button} pressed!')
        if button == 2:
            await self.exit_read_board_and_select_color()
        if button == 1:
            log.info("New Game without PGN save")
            self.skip_pgn = True
            self.running = False
            self.force_quit = True

    def check_and_display_check(self):
        if self.is_check:
            # find king in check
            square = filter(lambda p: p.piece and p.piece.piece_type == chess.KING and p.piece.color == self.board.turn,
                            board_state_as_square_and_piece(self.board_state))
            square = list(square)
            if len(square) > 0:
                self.to_blink = chess.SquareSet([square[0][0]])

    async def check_quit(self) -> bool:
        """
        Check if game should end because the kings were placed in the middle in specific ways
        if both kings are on black: black wins
        if both kings are on white: white wins
        if mixed and vertical: draw
        if mixed and horizontal: quit completely
        """

        relevant_positions = filter(lambda s_p: (3 <= chess.square_rank(s_p.square) <= 4 and
                                                 3 <= chess.square_file(s_p.square) <= 4),
                                    board_state_as_square_and_piece(self.board_state))  # should always be 4
        d5, e5, d4, e4 = map(lambda pos: pos[1].piece_type == chess.KING if pos[1] else False, relevant_positions)
        if d5 and e4:  # both on white TODO: maybe add online resign/draw offer
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
        diffs = self.compare_board_state_to_fen(self.board.fen())
        # turn off any lights that might still be on
        self.to_blink.clear()
        self.to_light.clear()
        if self.undo_loop and len(diffs) == 0:
            self.undo_loop = False
        if diffs and not self.maybe_read:
            self.fixing_board = True
            log.info("board incorrect!\nplease fix")
            suggested = False
            while diffs:
                if self.force_quit:
                    self.fixing_board = False
                    return
                # check if we want to override an AI move
                if self.undo_loop and len(diffs) == 2:
                    move1 = chess.Move(diffs[0][1], diffs[1][1])
                    move2 = chess.Move(diffs[1][1], diffs[0][1])
                    if move1 in self.board.legal_moves:
                        self.board.push(move1)
                        break
                    elif move2 in self.board.legal_moves:
                        self.board.push(move2)
                        break
                # check if we want to quit/reset the game
                self.winner = None
                want_to_quit = await self.check_quit()
                if self.inited and want_to_quit:
                    self.running = False
                    return
                # Calculate LEDs needed to fix all diffs
                led_pairs = fen_diff_leds(diffs)
                # generally only display LEDs to fix 1 diff
                to_display = led_pairs[0]
                if len(to_display) == 1:  # if only 1 LED needed
                    self.to_blink = to_display  # blink LED instead of lighting it
                    self.to_light.clear()
                else:
                    if not suggested:
                        self.to_blink.clear()
                    if self.castling and len(led_pairs) > 1:
                        # if the AI is doing a castling move we want to display the King pair
                        # if no king move exists display any pair
                        for p in led_pairs:
                            if chess.E8 in p or chess.E1 in p:
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
                diffs = self.compare_board_state_to_fen(self.board.fen())
            log.info(f"board fixed!\n{self.board.fen()}")
            self.fixing_board = False
            if task and not task.done():
                task.cancel()
            await asyncio.sleep(0.2)
        else:
            test = self.board_state_as_fen()
            log.info(f"board correct:\n{chess.Board(test)}")
        # Move is Fixed
        self.castling = False
        self.to_light.clear()
        self.to_blink.clear()
        if self.undo_loop and len(self.board.move_stack) > 0:
            next_undo = self.board.peek()
            self.to_light = chess.SquareSet([next_undo.from_square, next_undo.to_square])
        self.move_start = []
        self.move_end = None

    async def ai_move(self):
        would_have_done_task = None
        if self.options.show_would_have_done_move and not self.is_online_game:
            has_player_move = len(self.board.move_stack) > 0
            if has_player_move:
                player_move = self.board.pop()
                min_time = (self.engine_manager.limit.time if self.engine_manager.limit.time else 0) + 5.0
                would_have_done_task = asyncio.create_task(self.engine_manager.get_move_suggestion(self.board.copy(),
                                                                                         min_time=min_time))
                self.board.push(player_move)
        if self.is_online_game:
            play = await self.lichess.opponent_move(sleep_fun=lambda: self.blink_tick(sleep_time=0.5))
            if play is None:
                self.running = False
                self.winner = self.lichess.game.winner
                return
            raw_move = chess.Move.from_uci(play)
        else:
            raw_move = await self.engine_manager.get_cpu_move(self.board)

        move = f"{raw_move}"
        log.info("generated Move: %s", move)
        if self.board.is_castling(raw_move):
            self.castling = True
        self.board.push_uci(move)
        await self.fix_board(task=would_have_done_task)
        self.player_turn = True

    async def find_start_move(self):
        # find a move_start that has legal moves
        for legal_move in self.board.legal_moves:
            for square, _ in self.move_start:
                if legal_move.from_square == square:
                    return square
        return None

    async def player_move(self):
        start_move = await self.find_start_move()
        if start_move == None and len(self.move_start) > 0:
            start_move = self.move_start[0][0]
        if start_move != None and self.move_end and start_move != self.move_end[0]:
            move = chess.Move(start_move, self.move_end[0])
            if self.player_turn:
                moves = list(filter(lambda m: m.from_square == move.from_square and m.to_square == move.to_square,
                                    self.board.legal_moves))
                if len(moves) > 1:  # more than 1 move is legal -> promotion move
                    # we have to figure out the new piece
                    move.promotion = self.move_end[1].piece_type
                if await self.maybe_wait_for_board_settle():
                    self.move_start = []
                    self.move_end = None
                    return
                if not await self.player_move_is_valid(move):
                    if not await self.want_to_undo(move):
                        log.info(f"illegal move {move.uci()}\n{self.board}")
                    await self.fix_board()
            self.move_start = []
            self.move_end = None

    async def maybe_wait_for_board_settle(self):
        if not self.options.dragging_detection:
            return False
        while await self.board_has_changed(timeout=self.options.dragging_timeout):
            pass
        # do legal move check through fen compare
        # generate all legal fens
        board = self.board.copy()

        def move_to_fen(m):
            nonlocal board
            board.push(m)
            fen = board.board_fen()
            board.pop()
            return fen, m

        legal_fens = map(move_to_fen, self.board.legal_moves)
        # see if cur fen is legal
        bs = self.board_state_as_fen()
        f_m = filter(lambda m: m[0] == bs, legal_fens)
        f_ms = list(f_m)
        if len(f_ms) > 0:
            await self.player_move_is_valid(f_ms[0][1])
            return True
        return False

    async def player_move_is_valid(self, move):
        if self.board.is_legal(move):
            self.board.push(move)
            log.info(self.board)
            log.info("Move-stack: %s", list(map(lambda m: m.uci(), self.board.move_stack)))
            log.info("Player move: %s", move.uci())
            if self.is_online_game:
                if self.lichess.game and self.lichess.game.ended:
                    self.running = False
                    self.winner = self.lichess.game.winner
                    return True
                self.lichess.make_move(move)
            self.to_blink.clear()
            self.to_light.clear()
            self.player_turn = self.board.turn == self.player_color
            self.undo_loop = False
            return True
        return False

    async def want_to_undo(self, move):
        if len(self.board.move_stack) > 0 and chess.Move(move.to_square, move.from_square) == self.board.peek():
            log.info("undoing moves!")
            self.board.pop()
            if len(self.board.move_stack) < 1:
                self.to_light.clear()
                self.to_blink.clear()
                if self.board.turn != self.player_color:
                    await self.ai_move()
                self.move_start = []
            else:
                self.board.pop()
            self.undo_loop = True
            return True
        return False

    async def exit_read_board_and_select_color(self, wants_online: "typing.Literal['challenge', 'seek'] | None" = None,
                                               seek_info=None):
        log.info(f"in exit and select... {wants_online}")
        self.running = False
        self.force_quit = True
        self.should_read = wants_online is None
        self.skip_pgn = True
        self.is_online_game = wants_online is not None
        self.online_seek_info = seek_info if wants_online == 'seek' else None
        self.next_game_online = wants_online

    async def game_loop(self):
        if not self.engine_manager.engines_running:
            await self.engine_manager.init_engines()
        if self.options.play_animations:
            await self.play_animation(animations.start_anim)
        else:
            await asyncio.sleep(1)  # wait for board to settle
        self.winner = None
        self.inited = True
        await self.request_battery_status()
        if self.is_online_game:
            if self.next_game_online == 'challenge':
                self.lichess.await_challenge()
            elif self.next_game_online == 'seek':
                clock_time, increment, rated, color, rating_range = self.online_seek_info
                log.info('Seeking Online game.')
                self.lichess.seek_game(clock_time=clock_time, increment=increment, rated=rated, color=color,
                                       rating_range=rating_range)
            else:
                log.warning("Finding online game Failed... You should probably restart.")
                return
            self.next_game_online = None
            log.info(self.lichess.game_info)
            self.board = chess.Board(self.lichess.game_info['fen'])
            log.info(self.board.fen())
            self.player_color = self.lichess.game_info['color'] == 'white'
            self.force_quit = False
            self.player_color_select = False
        else:
            while self.force_quit and not self.is_online_game:
                self.force_quit = False
                await self.maybe_read_board()
            await self.select_player_color()
        self.player_turn = self.board.turn == self.player_color
        await self.fix_board()
        self.to_blink.clear()
        self.to_light.clear()
        if self.options.play_animations:
            await self.play_animation(animations.game_start_amin, sleep_time=0.1)
        self.running = True
        # all initializing is done to loop can finally begin
        while self.running and not self.force_quit:
            self.is_check = self.board.is_check()
            if self.board.is_checkmate():
                await self.play_animation(animations.check_mate_anim)
                log.info("checkmate!")
                self.running = False
                self.winner = not self.board.turn
                continue
            elif self.board.is_stalemate():
                await self.play_animation(animations.stalemate_anim)
                # noinspection SpellCheckingInspection
                log.info("Remis!")
                self.running = False
            if self.player_turn:
                # self.check_and_display_check()
                await self.player_move()
            else:
                log.info(f"Openings: {self.engine_manager.print_openings(self.board)}")
                await self.ai_move()
                log.info(f"Openings: {self.engine_manager.print_openings(self.board)}")
            await self.blink_tick(sleep_time=0.3)
        log.info(f'winner was {self.winner}!')
        if not self.skip_pgn:
            self.engine_manager.write_to_pgn(self)
        if self.more_games:
            # reset this object and call game_loop again
            self.setup()
            await self.game_loop()
        await self.engine_manager.quit_chess_engines()
        self.bt_running = False

    async def maybe_read_board(self):
        if self.should_read:
            if self.board_state_as_fen() == chess.Board().board_fen():
                self.board = chess.Board()
            else:
                castling = self.generate_castling_rights()
                self.board = chess.Board(
                    f'{self.board_state_as_fen()} {"w" if self.player_color == chess.WHITE else "b"} {castling}')
                self.have_read_board = True
            log.info(f'Read board state:\n{self.board.fen()}')
            self.should_read = False
        else:
            log.info("Board settled")
            await self.fix_board()

    def generate_castling_rights(self):
        castling = ''
        kings = filter(lambda p: p.piece and p.piece.piece_type == chess.KING,
                       board_state_as_square_and_piece(self.board_state))
        wk = bk = None
        for k in kings:
            if k[1].color == chess.WHITE:
                wk = k[0]
            else:
                bk = k[0]
        white_rooks = []
        black_rooks = []
        for square, piece in board_state_as_square_and_piece(self.board_state):
            if piece and piece.piece_type == chess.ROOK:
                (white_rooks if piece.color == chess.WHITE else black_rooks).append(square)
        if wk == chess.E1:
            # white castling rights
            if len(white_rooks) > 0:
                if white_rooks[0] == chess.H1 or (len(white_rooks) > 1 and white_rooks[1] == chess.H1):
                    castling += 'K'
                if white_rooks[0] == chess.A1 or (len(white_rooks) > 1 and white_rooks[1] == chess.A1):
                    castling += 'Q'
        if bk == chess.E8:
            # black castling rights
            if len(black_rooks) > 0:
                if black_rooks[0] == chess.H8 or (len(black_rooks) > 1 and black_rooks[1] == chess.H8):
                    castling += 'k'
                if black_rooks[0] == chess.A8 or (len(black_rooks) > 1 and black_rooks[1] == chess.A8):
                    castling += 'q'
        return castling if len(castling) > 0 else '-'

    async def select_player_color(self):
        if self.is_online_game:
            return
        if self.player_color is None:
            self.player_color = chess.WHITE
            self.player_turn = True
            self.player_color_select = True
            log.info('select a color by picking up a king')
            if self.options.play_animations:
                await self.play_animation(animations.pick_anim, sleep_time=0.4)
            self.to_blink = chess.SquareSet(self.find_king_squares())
        while self.player_color_select and not self.force_quit:
            await self.blink_tick(sleep_time=0.5)
        self.to_blink.clear()
        self.to_light.clear()
        if self.have_read_board and self.player_color != self.board.turn:
            self.board.turn = self.player_color

    def find_king_squares(self):
        return map(lambda s: s[0], filter(lambda p: p.piece and p.piece.piece_type == chess.KING,
                                          board_state_as_square_and_piece(self.board_state)))


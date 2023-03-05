import asyncio
import math

import animations
from data2fen import convert_to_fen, pieces_from_data
from constants import convertDict
from ChessnutAir import ChessnutAir, loc_to_pos
from GameOfChess import GameOfChess
import chess
from bleak import BleakError

from fencompare import compare_chess_fens, fen_diff_leds

"""
Mindmap:

aufstellung der startposition = neues game
wenn stellung aufgestellt, dann ist der player turn = der letzte könig der gesetzt wurde
analysefunktion bzw. schiedsrichterfunktion

funktionsweise pi:
-an
- programm wird gestartet -> sucht nach board
-> vielleicht shutdown nach 5 min
- findet board -> ließt startpos aus
- fragt nach spielerfarbe
- startet game 
- wenn matt dann restart gameloop
- wenn beide könige in der mitte (diagonal oder nebeneinander) restart gameloop, 
    wenn beide weißen damen nebeneinander shutdown
"""


class Game(ChessnutAir):
    def __init__(self, board_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", turn="w", castle="KQkq",
                 player_color=None, read_board=False, no_help=False, show_valid_moves=True, play_animations=True):
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
        self.board = chess.Board(f"{board_fen} {turn} {castle} - 0 1")
        self.target_fen = ""
        self.waiting_for_move = True
        self.undo_loop = False
        self.player_turn = False
        self.game = GameOfChess()
        self.more_games = True
        self.winner = None
        self.inited = False
        self.cur_fen = " "
        self.show_valid = show_valid_moves
        self.is_check = False
        self.play_animations = play_animations

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
        self.waiting_for_move = True
        self.undo_loop = False
        self.player_turn = False
        self.winner = None
        self.inited = False
        self.is_check = False

    def boardstate_as_fen(self):
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

    async def led_score(self, score=None):
        # check if score exists, else await score
        score = score if score else int((await self.game.get_score(self.board)).score())
        print(score)
        # Max score is divided into increments via half of the LED matrix.
        # I.e. if leds has 8 entries, increments = 200/ 4 = 50
        leds = ['a4', 'a3', 'a2', 'a1', 'a8', 'a7', 'a6', 'a5']
        max_score = 200
        increments = (max_score*2)/len(leds)
        # return the score relative to the increments that we just created
        score_in_increments = int(math.ceil(score/increments))  # ceiling to only have 0 leds at scaore = 0
        # make sure we are within -len(leds)/2<score_in_increments<len(leds)/2
        score_in_increments = max(min(score_in_increments, len(leds)//2), -len(leds)//2)
        # define the LEDs we need to light for this move, and light them!
        start = 0 if score_in_increments >= 0 else score_in_increments+1
        end = score_in_increments if score_in_increments > 0 else len(leds)
        self.to_blink = leds[start:end]
        await self.change_leds(self.to_blink)
        await asyncio.sleep(1.4)
        await self.blink_tick()

    async def player_king_hover_action(self):
        if self.player_color_select:
            print("Selected White")
            self.player_color = chess.WHITE
            self.player_color_select = False
        else:
            move = await self.game.getmovesuggestion(self.board)
            print(f"suggesting move: {move}")
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
        async def king_hover_action():
            if (self.player_color == chess.WHITE and p_str == 'K')\
                    or (self.player_color == chess.BLACK and p_str == 'k'):
                await self.player_king_hover_action()
            elif p_str == 'K' or p_str == 'k':
                await self.cpu_king_hover_action()
        pos = loc_to_pos(location)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} down")
        if self.player_turn and len(self.move_start) > 0:
            self.to_light = []
            ms = await self.find_start_move()
            if ms and ms != pos:
                self.move_end = (pos, p_str)
                self.to_blink = []
            else:
                await king_hover_action()

    async def piece_up(self, location, piece_id):
        pos = loc_to_pos(location)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} up")
        self.to_light.append(pos)
        self.move_end = None
        self.move_start.append((pos, p_str))
        if self.show_valid:
            for move in self.board.legal_moves:
                m_str = f"{move}"
                from_square = m_str[:2]
                if from_square == pos:
                    self.to_blink.append(m_str[2:])
                to_square = m_str[2:]
                if to_square == pos:
                    self.to_blink.append(m_str[:2])
        if len(self.board.move_stack) > 0:
            undo = f"{self.board.peek()}"
            if undo[2:] == pos:
                self.to_blink.append(undo[:2])

    def check_check(self):
        if self.is_check:
            # find king in check
            pos = filter(lambda p: p[1] == 'k' or p[1] == 'K',
                         enumerate(map(lambda p: convertDict[p], pieces_from_data(self.board_state))))
            pos = list(pos)
            if self.board.turn == chess.WHITE:
                pos = filter(lambda p: p[1] == 'K', pos)
            else:
                pos = filter(lambda p: p[1] == 'k', pos)
            pos = list(pos)
            if len(pos) > 0:
                pos = pos[0]
                x = pos[0] % 8
                y = 8-pos[0] // 8
                pos = "abcdefgh"[x]+str(y)
                self.to_blink = [pos]

    async def blink_tick(self):
        self.tick = not self.tick
        self.check_check()
        if self.tick:
            await self.change_leds(self.to_blink+self.to_light)
        else:
            await self.change_leds(self.to_light)

    async def check_quit(self) -> bool:
        """
        Special quit checks:
            e4-K e5-K d4-k d5-k
        """
        relevant_poss = []

        for i, piece in enumerate(pieces_from_data(self.board_state)):
            # i(0) = A1, i(63) = H8
            x = i % 8
            y = i // 8
            if (x == 3 or x == 4) and (y == 3 or y == 4):  # -> four field in the center
                relevant_poss.append(convertDict[piece])
            if i > 47:
                break
        d5, e5, d4, e4 = map(lambda pos: pos == 'k' or pos == 'K', relevant_poss)
        if d5 and e4:  # both on white
            # white wins
            self.winner = chess.WHITE
            return True
        elif d4 and e5:  # both on black
            self.winner = chess.BLACK
            return True
        elif (e4 and e5) or (d4 and d5):  # Draw
            return True
        elif (e4 and d4) or (e5 and d5):  # we want to quit completly
            self.more_games = False
            return True
        return False

    async def fix_board(self, task=None):
        diffs = compare_chess_fens(self.board.fen(), self.boardstate_as_fen())
        self.to_blink = self.to_light = []  # turn off any lights that might still be on
        if diffs:
            print("board incorrect!\nplease fix")
            suggested = False
            while diffs:
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
                else:
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
                # actually change LEDs to light or blink
                await self.blink_tick()
                # loop is done. wait a bit and then recalculate the diffs
                await asyncio.sleep(0.2)
                diffs = compare_chess_fens(self.board.fen(), self.boardstate_as_fen())
            print(f"board fixed!\n{self.board.fen()}")
            if not task.done():
                task.cancel()
            await asyncio.sleep(0.2)
        else:
            test = self.boardstate_as_fen()
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
        player_move = self.board.pop()
        would_have_done_task = asyncio.create_task(self.game.getmovesuggestion(self.board.copy()))
        self.board.push(player_move)
        rmove = await self.game.getcpumove(self.board)
        move = f"{rmove}"[:4]
        print("generating Move!", move)
        if self.board.is_castling(rmove):
            print("ai is right")
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
                if self.board.is_legal(chess.Move.from_uci(move)):
                    self.board.push_uci(move)
                    print(self.board)
                    print("Player move: ", move)
                    self.to_blink = self.to_light = []
                    self.player_turn = False
                    self.undo_loop = False
                else:
                    # check if we want to undo a move
                    if len(self.board.move_stack) > 0 and move[2:] + move[:2] == f"{self.board.peek()}":
                        print("undoing moves!")
                        self.board.pop()
                        if len(self.board.move_stack) < 1:
                            self.to_light = self.to_blink = []
                            await self.ai_move()
                        else:
                            self.board.pop()
                        self.undo_loop = True
                    else:
                        print(f"illegal move {move}\n{self.board}")
                    await self.fix_board()
            self.move_start = []
            self.move_end = None

    async def game_loop(self):
        if self.play_animations:
            await self.play_animation(animations.start_anim)
        else:
            await asyncio.sleep(1)  # wait for board to settle
        self.winner = None
        await self.maybe_read_board()
        self.inited = True
        await self.select_player_color()
        self.player_turn = self.board.turn == self.player_color
        self.to_blink = self.to_light = []
        if self.play_animations:
            await self.play_animation(animations.game_start_amin, sleep_time=0.1)
        self.running = True
        # all initializing is done to loop can finally begin
        while self.running:
            await self.blink_tick()
            self.is_check = self.board.is_check()
            if self.board.is_checkmate():
                await self.play_animation(animations.check_mate_anim)
                print("checkmate!")
                self.running = False
                self.winner = not self.board.turn
                continue
            elif self.board.is_stalemate():
                await self.play_animation(animations.stalemate_anim)
                print("Remis!")
                self.running = False
            if self.player_turn:
                await self.player_move()
            else:
                self.print_openings()
                await self.ai_move()
                self.print_openings()

            await asyncio.sleep(0.3)
        print(f'winner was {self.winner}!')
        # save PGN here
        self.game.write_to_pgn(self)
        if not self.more_games:
            return
        # reset this object and call game_loop again
        self.setup()
        await self.game_loop()
        self.game.quitchess()

    async def maybe_read_board(self):
        if self.should_read:
            self.board = chess.Board(f'{self.boardstate_as_fen()} {"w" if self.player_color == chess.WHITE else "b"}')
            print(f'Read boardstate:\n{self.board}')
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
            await self.blink_tick()
            await asyncio.sleep(0.5)

    def print_openings(self):
        cur_var = self.game.ecopgn
        for n in self.board.move_stack:
            if cur_var.has_variation(n):
                cur_var = cur_var.variation(n)
            else:
                cur_var = None
                break
        if cur_var:
            print('\n'.join(reversed(cur_var.comment.split('\n'))))
        else:
            print(f'not openers found: {" ".join(map(lambda m: m.uci(), self.board.move_stack))}')


async def go():
    b = Game(show_valid_moves=True)
    while not b.device:
        await b.discover()
    try:
        await b.run()
    except BleakError:
        print("Board Disconnected. Retring connection.")
        await go()
        quit()
    except KeyboardInterrupt:
        print(b.board.fen())
        quit()

asyncio.run(go())

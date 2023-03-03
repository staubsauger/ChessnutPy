import asyncio
from data2fen import convert_to_fen
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from ChessnutAir import ChessnutAir, loc_to_pos
from GameOfChess import GameOfChess
import chess
from chess.engine import Cp
import random

from fencompare import compare_chess_fens, fen_diff_leds

"""
Mindmap:

aufstellung der startposition = neues game
wenn stellung aufgestellt, dann ist der player turn = der letzte könig der gesetzt wurde
analysefunktion bzw. schiedsrichterfunktion


"""
class Game(ChessnutAir):
    def __init__(self, board_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", turn="w", castle="KQkq",
                 player_color="b", read_board=False):
        ChessnutAir.__init__(self)
        self.should_read = read_board
        self.target_move = None
        self.move_end = None
        self.move_start = []
        self.running = False
        self.tick = False
        self.castling = False
        self.to_blink = []
        self.to_light = []
        self.player_color = chess.WHITE if player_color == "w" else chess.BLACK
        self.board = chess.Board(f"{board_fen} {turn} {castle} - 0 1")
        self.target_fen = ""
        self.waiting_for_move = True
        self.undo_loop = False
        self.player_turn = False
        self.game = GameOfChess()

    def boardstate_as_fen(self):
        self.cur_fen = convert_to_fen(self.boardstate)
        return self.cur_fen

    async def suggest_move(self, move):
        move = move[:4]
        self.to_blink = [move[2:], move[:2]]
        await self.change_leds(self.to_blink)
        await asyncio.sleep(1.0)

    async def led_score(self, ):
        score = int(self.game.get_score(self.board).score())
        print(score)

        if 50 > score >= 0:
            self.to_blink=['a4']
            await self.change_leds(self.to_blink)
        elif 50 < score <= 100:
            self.to_blink=['a4', 'a3']
            await self.change_leds(self.to_blink)
        elif 100 < score <= 150:
            self.to_blink=['a4', 'a3', 'a2']
            await self.change_leds(self.to_blink)
        elif score > 150:
            self.to_blink=['a4', 'a3', 'a2', 'a1']
            await self.change_leds(self.to_blink)

        elif score < 0 <= -50:
            self.to_blink = ['a5']
            await self.change_leds(self.to_blink)
        elif score < -50 <= -100:
            self.to_blink = ['a5', 'a6']
            await self.change_leds(self.to_blink)
        elif score < -100 <= -150:
            self.to_blink = ['a5', 'a6', 'a7']
            await self.change_leds(self.to_blink)
        elif score < -150:
            self.to_blink = ['a5', 'a6', 'a7', 'a8']
            await self.change_leds(self.to_blink)
        await asyncio.sleep(1.0)

    async def piece_down(self, location, piece_id):
        async def king_hover_action():
            async def player_king_action():
                move = self.game.getmovesuggestion(self.board)
                print(f"suggesting move: {move}")
                await self.suggest_move(move)
                self.move_end = None
                self.move_start = []

            if not ms or ms == pos:
                print("white King hovered")
                if self.player_color and p_str == 'K':
                    await player_king_action()
                elif not self.player_color and p_str == 'k':
                    await player_king_action()
                else:
                    print("LED Score")
                    await self.led_score()


            # elif (not ms or ms == pos) and p_str == 'k':
            #     print("black King hovered")
            #     if not self.player_color:
            #         await player_king_action()

        pos = loc_to_pos(location)
        print("Location", pos)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} down")
        if self.player_turn and len(self.move_start) > 0:
            print("playercolor is: ", self.player_color)
            self.to_light = []
            await self.change_leds(self.to_light)
            ms = await self.find_start_move()
            print("MS= ", ms)
            if ms != pos:
                self.move_end = (pos, p_str)
                self.to_blink = []
            # if (not ms or ms == pos) and p_str == 'K' or p_str == 'k': # hier stimmt was nicht. K kann keine züge machen
            await king_hover_action()
                # move = self.game.getmovesuggestion(self.board)
                # print(f"suggesting move: {move}")
                # await self.suggest_move(move)
                # self.move_end = None
                # self.move_start = []

            self.to_blink = []


    async def piece_up(self, location, piece_id):
        pos = loc_to_pos(location)
        p_str = convertDict[piece_id]
        print(f"piece: {p_str} at {pos} up")
        self.to_light.append(pos)
        await self.change_leds(self.to_light)
        self.move_end = None
        self.move_start.append((pos, p_str))
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


    async def blink_tick(self):
        self.tick = not self.tick
        if self.tick:
            await self.change_leds(self.to_blink+self.to_light)
        else:
            await self.change_leds(self.to_light)

    async def fix_board(self):
        diff = compare_chess_fens(self.board.fen(), self.boardstate_as_fen())
        if diff:
            print("board incorrect!\nplease fix")
            while diff:
                led_pairs = fen_diff_leds(diff)
                first = led_pairs[0]
                if len(first) == 1:
                    self.to_blink = first
                    self.to_light = []
                else:
                    if self.castling and len(led_pairs) > 1:
                        led_pair = led_pairs[0]
                        for p in led_pairs:
                            if p[0].startswith("e"):
                                led_pair = p
                                break
                        self.to_light = led_pair
                    else:
                        self.to_light = first
                    self.to_blink = []
                await self.blink_tick()
                await asyncio.sleep(0.2)
                diff = compare_chess_fens(self.board.fen(), self.boardstate_as_fen())
            print(f"board fixed!\n{self.board.fen()}")
            await asyncio.sleep(0.2)
        else:
            test = self.boardstate_as_fen()
            print(f"board correct:\n{chess.Board(test)}")
        self.castling = False
        self.to_light = self.to_blink = []
        if self.undo_loop and len(self.board.move_stack) > 0:
            next_undo = f"{self.board.peek()}"
            self.to_light = [next_undo[:2], next_undo[2:]]
        await self.change_leds([])
        self.move_start = []
        self.move_end = None

    async def ai_move(self):
        # generate move
        rmove = self.game.getcpumove(self.board)
        move = f"{rmove}"[:4]
        print("generating Move!", move)
        if self.board.is_castling(rmove):
            print("ai is right")
            self.castling = True
        self.board.push_san(move)
        await self.fix_board()
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
                if moves != [] and len(moves) > 1:
                    move += self.move_end[1]
                if self.board.is_legal(chess.Move.from_uci(move)):
                    self.board.push_san(move)
                    print(self.board)
                    print("Users last move: ", move)
                    self.to_blink = self.to_light = []
                    self.player_turn = False
                    self.undo_loop = False
                else:
                    if len(self.board.move_stack) > 0 and move[2:] + move[:2] == f"{self.board.peek()}":  # check if we want to undo a move
                        print("undoing moves!")
                        self.board.pop()
                        if len(self.board.move_stack) < 1:
                            self.to_light = self.to_blink = []
                            await self.change_leds([])
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
        await asyncio.sleep(1)  # wait for board to settle
        if self.should_read:
            self.board = chess.Board(f'{self.boardstate_as_fen()} {"w" if self.player_color == chess.WHITE else "b"}')
            print(f'Read boardstate:\n{self.board}')
            self.should_read = False
        else:
            print("Board settled")
            await self.fix_board()
        # TODO: hier durch anheben entscheiden welche farbe man spielt (hebe könig der farbe)
        self.player_turn = self.board.turn == self.player_color

        self.running = True
        while self.running:
            await self.blink_tick()
            if self.board.is_checkmate():
                print("checkmate!")
                self.running = False
                self.game.quitchess()
                continue
            if self.player_turn:
                await self.player_move()
            else:
                await self.ai_move()

            await asyncio.sleep(0.3)

async def go():
    b = Game(player_color='w')#, read_board=True)  #board_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", turn='w', player_color='w')
    while not b.device:
        await b.discover()
    try:
        await b.run()
    except KeyboardInterrupt:
        print(b.board.fen())

asyncio.run(go())

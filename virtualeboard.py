class Eboard:
    def __init__(self) -> None:
        self.boardstatus = None
        self.onleds = [0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x08, 0x00] # all off
        self.new_game_arr = bytearray(b'\x01$X#1\x85DDDD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00wwww\xa6\xc9\x9bjy\xe7G\x00')

    def printboard(boardstatus):
        pass

    def ledon(input):
        pass

    def ledoff(input):
        pass


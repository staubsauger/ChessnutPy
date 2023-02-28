from constants import convertDict, MASKLOW


# piece_pos_x = location % 8  # -> rest von location//8 (13 % 8 = 5 <=> 13= 8*1+5)
# piece_pos_y = location // 8  # -> floor(location/8) (13 // 8 = 1)
# location = piece_pos_y*8+piece_pos_x
# print(piece_str)
# location += 1

def pieces_from_data(data):
    """"
    data:  [0x14,0x00,0xa5] (size = 32), 0x1C -> Kq
    makes an interator (generator) like and works like an array of [" ", " ", "q", " ", ... ]
    to do this:
     -data is saved
    """
    for i in range(len(data)):
        double_field = data[(i // 8) * 8 + (8 - i % 8)]
        lfield = double_field & 0xf
        rfield = double_field >> 4
        yield lfield
        yield rfield


def convert_to_fen(data):
    """"
    convert data to fen
    """
    result = ""
    empty_count = 0
    x_pos = 0
    for piece in pieces_from_data(data):
        if x_pos == 8:
            x_pos = 0
            if empty_count > 0:
                result += str(empty_count)
                empty_count = 0
            result += "/"
        x_pos += 1
        piece_str = convertDict[piece]
        if piece_str == " ":
            empty_count += 1
            continue
        if empty_count > 0:
            result += str(empty_count)
            empty_count = 0
        result += piece_str
    return result

def get_fen(data):
    return convert_to_fen(data)

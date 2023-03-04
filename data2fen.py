from constants import convertDict, MASKLOW

def pieces_from_data(data):
    """"
    data:  [0x14,0x00,0xa5] (size = 32), 0x1C -> Kq
    makes an interator (generator) that  works like an array of [" ", " ", "q", " ", ... ]
    to do this:
     -data is saved
    """
    for i in range(len(data)):
        x = i % 4
        y = i // 4
        new_x = 3 - x
        new_i = (y * 4) + new_x
        double_field = data[new_i]
        rfield = double_field & 0xf
        lfield = double_field >> 4
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
    if empty_count > 0:
        result += str(empty_count)
    return result

"""
get a move like "e2e4" and set the bytearray[0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00]
"""
convLetterDict = {
    "a" : 128,
    "b" : 64,
    "c" : 32,
    "d" : 16,
    "e" : 8,
    "f" : 4,
    "g" : 2,
    "h" : 1,
}

convNumberDict = {
    "1" : 8,
    "2" : 7,
    "3" : 6,
    "4" : 5,
    "5" : 4,
    "6" : 3,
    "7" : 2,
    "8" : 1,

} 

def turnOnat(move_p1, move_p2, bytearr):
    result = bytearray(bytearr) # bytearray([0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    result = result[2:10]
    result[convNumberDict[move_p2]-1] += convLetterDict[move_p1]
    print("Turn On", result)
    return bytearray([0x0A, 0x08]) + result

def turnOffat(move_p1, move_p2, bytearr):
    result = bytearr # bytearray([0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    result = result[2:10]

    if result[convNumberDict[move_p2]-1] != 0x00:
        result[convNumberDict[move_p2]-1] -= convLetterDict[move_p1]
    else:
            print(move_p1, move_p2 ,"already off")
    print("Turn Off", result)
    return bytearray([0x0A, 0x08]) + result


# print(turnOnat("e", "2", bytearray([0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])))

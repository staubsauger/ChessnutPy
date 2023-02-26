""" Constant used in the program"""
# When the board is first connected it is necessary to send it a three byte initialisation code:
INITIALIZASION_CODE = b'\x21\x01\x00'
# The board will then send back a three byte confirmation code:
CONFIRMATION_CHARACTERISTICS = b'\x21\x01\x00'
# The signals from the board consist of a sequence of 38 bytes. The first two are:
HEAD_BUFFER = b'\x01\x24'
#  Communications using BLE
DEVICELIST = ['Chessnut Air', 'Smart Chess']
WRITECHARACTERISTICS = '1B7E8272-2877-41C3-B46E-CF057C562023'
READCONFIRMATION = '1B7E8273-2877-41C3-B46E-CF057C562023'
READDATA = '1B7E8262-2877-41C3-B46E-CF057C562023'

# Within each byte the lower 4 bits represent the 
# first square and the higher 4 bits represent the 
# second square
MASKLOW = 0b00001111

# Each square has a value specifying the piece:
convertDict = {0: " ",
               1: "q",
               2: "k",
               3: "b",
               4: "p",
               5: "n",
               6: "R",
               7: "P",
               8: "r",
               9: "B",
               10: "N",
               11: "Q",
               12: "K"
}

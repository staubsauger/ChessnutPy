""" Constant used in the program"""
# When the board is first connected it is necessary to send it a three byte initialisation code:
INITIALIZATION_CODE = b'\x21\x01\x00'
# The board will then send back a three byte confirmation code:
CONFIRMATION_CODE = b'\x21\x01\x00'
# The signals from the board consist of a sequence of 38 bytes. The first two are:
HEAD_BUFFER = b'\x01\x24'
REQUEST_BATTERY_CODE = b'\x29\x01\x00'
#  Communications using BLE
DEVICE_LIST = ['Chessnut Air', 'Smart Chess']
WRITE_CHARACTERISTIC                = '1B7E8272-2877-41C3-B46E-CF057C562023'
READ_CONFIRMATION_CHARACTERISTIC    = '1B7E8273-2877-41C3-B46E-CF057C562023'
READ_DATA_CHARACTERISTIC            = '1B7E8262-2877-41C3-B46E-CF057C562023'
OTHER_CHARACTERISTICS = ["1B7E8271-2877-41C3-B46E-CF057C562023", "1B7E8261-2877-41C3-B46E-CF057C562023",
                         "1b7e8281-2877-41c3-b46e-cf057c562023", "1b7e8283-2877-41c3-b46e-cf057c562023"]
ALL_CODES = {
        'maybe_wipe_otb': b'\x39\x01\x00',
        'init_code': b'\x21\x01\x00',
        'query_otb': b'\x31\x01\x00',
        'some_otb_cmd': b'\x33\x01\x00',
        'battery_status': b'\x29\x01\x00',
        'some_otb_cmd2': b'\x34\x01\x01',
        'set_otb_upload_mode': b'\x21\x01\x01'
    }

## more charecteristics
#                                      "1B7E8271-2877-41C3-B46E-CF057C562023" unknown
#                                      "1B7E8272-2877-41C3-B46E-CF057C562023" -> general write
#                                      "1B7E8273-2877-41C3-B46E-CF057C562023" -> akk and buttons
#                                      "1B7E8261-2877-41C3-B46E-CF057C562023" unknown
#                                      "1B7E8262-2877-41C3-B46E-CF057C562023" -> read board
#                                      "1b7e8281-2877-41c3-b46e-cf057c562023" unknown
#                                      "1b7e8283-2877-41c3-b46e-cf057c562023" unknown why public?

# Within each byte the lower 4 bits represent the 
# first square and the higher 4 bits represent the 
# second square
MASK_LOW = 0b00001111

# Each square has a value specifying the piece:
convertDict = {0: " ",
               1: "q",  # 0b00000001
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
               12: "K"}


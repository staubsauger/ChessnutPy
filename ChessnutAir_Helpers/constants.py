""" Constant used in the program"""
DEVICE_LIST = ['Chessnut Air', 'Smart Chess']
NONEXISTENT_CHARACTERISTICS = ["1B7E8271-2877-41C3-B46E-CF057C562023", "1B7E8261-2877-41C3-B46E-CF057C562023",
                               "1b7e8281-2877-41c3-b46e-cf057c562023"]  # maybe for another board?


class BtCharacteristics:
    write =             '1B7E8272-2877-41C3-B46E-CF057C562023'# noqa
    read_misc_data =    '1B7E8273-2877-41C3-B46E-CF057C562023'# noqa
    read_board_data =   '1B7E8262-2877-41C3-B46E-CF057C562023'# noqa
    read_otb_data =     '1b7e8283-2877-41c3-b46e-cf057c562023'# noqa


class BtCommands:
    init_code =                     b'\x21\x01\x00'# noqa
    set_otb_upload_mode =           b'\x21\x01\x01'# noqa
    get_battery_status =            b'\x29\x01\x00'# noqa
    query_otb =                     b'\x31\x01\x00'# noqa
    is_app_ready =                  b'\x33\x01\x00'# noqa
    action_newest_data_tranfer =    b'\x34\x01\x01'# noqa
    action_data_transfer =          b'\x34\x01\x00'# noqa
    maybe_wipe_otb =                b'\x39\x01\x00'# noqa
    get_device_name =               b'\x2b\x01\x00'# noqa
    get_device_time =               b'\x26\x01\x00'# noqa
    set_leds_prefix =               b'\x0A\x08'# noqa


class BtResponses:
    heartbeat_code =    b'\x23\x01\x00' # noqa
    confirmation_code = b'\x21\x01\x00' # noqa
    head_buffer =       b'\x01\x24'     # noqa
    board_not_ready =   b'\x23\x01\x01' # noqa
    otb_count_prefix =  b'\x32\x01'     # noqa
    file_start =        b'\x37\x01\xbe' # noqa
    file_end =          b'\x37\x01\xed' # noqa
    file_size_prefix =  b'\x36\x08'     # noqa
    crc_len =           b'\x38\x04'     # noqa


# Each square has a value specifying the piece:
convertDict = {0: " ",
               1: "q",  # 0b0000_0001
               2: "k",
               3: "b",
               4: "p",
               5: "n",
               6: "R",
               7: "P",
               8: "r",
               9: "B",
               10: "N",
               11: "Q",  # 0b0000_1011
               12: "K"}

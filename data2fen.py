from constants import convertDict, MASKLOW

def get_pieces(data):
    temp_arr = []
    temp_arr2 = []

    for i in range(0,8):
        row = reversed(data[i*4:i*4+4])
        for b in row:
            left = convertDict[b >> 4]
            right = convertDict[b & MASKLOW]     
            temp_arr.append(left)
            temp_arr.append(right)
    for i in range(0,8):
        temp_arr2.append(temp_arr[0:8])
        for i in range(0,8):
            try: 
                temp_arr.pop(0)
            except IndexError:
                print("empty")
    
    return temp_arr2

def convert_to_fen(in_data):
    temp_str = ""
    for row in in_data:
        count = 0
        counter = 0
        for field in row:
            if field == " ":
                counter += 1
            elif field != " " and counter != 0:
                temp_str = temp_str + str(counter)
                counter = 0
                temp_str = temp_str + field
            elif field != " " and counter == 0:
                temp_str = temp_str + field
            count += 1
            if count == 8:
                if counter !=0:
                    temp_str = temp_str + str(counter)
                count = 0
        temp_str = temp_str + "/"
    temp_str = temp_str[:-1]
    # print("FEN from Board", temp_str)
    return temp_str

def get_fen(data):
    return convert_to_fen(get_pieces(data))

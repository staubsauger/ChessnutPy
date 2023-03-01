"""
a python function which compares two chess fens and returns on which fields a piece is wrong
"""

maskasletter = {
    0: "a",
    1: "b",
    2: "c",
    3: "d",
    4: "e",
    5: "f",
    6: "g",
    7: "h"
}

maskasnumber = {
    0 : 8,
    1 : 7,
    2 : 6,
    3 : 5,
    4 : 4,
    5 : 3,
    6 : 2,
    7 : 1,
}


def convert_fen(fen):
    """
    convert "r1bqkbnr/pppppppp/2n5/8/2P5/8/PP1PPPPP/RNBQKBNR w KQkq c6 0 2"
    to "r1bqkbnr/pppppppp/11n11111/11111111/11P11111/11111111/PP1PPPPP/RNBQKBNR"
    """
    fen = fen.split()[0]
    new_fen = ""
    for _ in fen:
        if _ not in ["k","K","q","Q","b","B","p","P","r","R","n","N", "/", "1"]:
            for count in range(int(_)):
                new_fen = new_fen+"1" 
        else: 
            new_fen = new_fen+_
    print("Your new fen ", new_fen)
    return new_fen

def compare_chess_fens(fen1, fen2):
    """
    takes fen1 and fen2 and returns which pieces are wrong on fen2
    fen like "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    return like [['P','d4'],['1', d2']] -> '1' = empty field,  'letters' = piece
    """
    fen1 = convert_fen(fen1).split("/")
    fen2 = convert_fen(fen2).split("/")
    print(fen1, fen2)
    differences = []
    count = 0 
    for i in range(len(fen1)): # für also 8
        
        if fen1[i] != fen2[i]:
            print("ungleich", fen1[i], fen2[i], maskasnumber[count])
            count2 = 0
            for b in range(len(fen2[i])): # also wieder 8 :)
                
                if fen1[i][b] != fen2[i][b]:
                    print("ungleich", fen1[i][b], fen2[i][b], str(maskasletter[count2])+str(maskasnumber[count]))
                    print("Piece:", fen2[i][b], "at ", str(maskasletter[count2])+str(maskasnumber[count]))
                    differences.append([fen2[i][b], str(maskasletter[count2])+str(maskasnumber[count])])
                count2 +=1
        count +=1
    return differences

fen1 = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
fen2 = "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1"
differences = compare_chess_fens(fen1, fen2)
print(differences)
# chessnutair
This is a program written in Python. You can connect your Chessnut Air eboard to your pc and play against chess engines.
At the moment we only support the Chessnut Air eboard and only via bluetooth. We tested the program with stockfish and 
the texel chess engines. Both work as intended so we can say, that all uci engines should work. Also the emulation of 
old chesscomputer via mame works, only the takeback function does not work at the moment. 

 * Supports Windows 10 (should work, but not tested)
 * Supports Linux distributions with BlueZ >= 5.43 (See Linux backend for more details)
 * OS X/macOS support (should work, but not tested)

So far, I have only tested this software on Linux.

## Installation and execution
 1. download code
 2. install dependencies (pip3 install -r requirements.txt)
 3. Optional: copy default.config to your $HOME/.config/chessnutair.config and edit it to your liking
 4. Execute python3 ./main.py
 

## Features
 1. Fix-board function: checks if the state of the board is valid and gives you hints, where pieces are wrong and 
 where you should place them
 2. If the board is correct, both squares with kings are lit. You can now pick a color by "hovering" a king (picking it 
 up and putting it back where it stood)
 3. While in game, you can hover you own king to get a hint for you next move. This is read out of the opening book 
 (.bin file) which you can configure in your own configuration. If no move was found in the opening book, you get a 
 suggestion from the engine which you can also configure in your config. Default is stockfish.
 4. If you hover the opponents king while a game is running, you get the score relative to white, indicated by the leds
 of the board.
 5. If you want to take back a move, you have to do the opponents move first, then you can take back this move and your
 own afterwards. The leds will help you find the last moves in the move stack. There is no limit. You can take back all
 moves until you get to the start position.
 6. There is also a rudimentary webinterface. It shows you the opening and other useful information. You can access the
interface via your web browser and 'http://localhost' or from another machine via the ip of the machine.
 7. Via the webinterface you can also access the ability to play online on lichess.org (chess.com maybe in the future)
 (you have to acquire a lichess-token and put it in your config)
 8. We also added the ability to start a new game by pushing the on/off button.
 9. The other button on the board reads the state of the board, so you can play any position you want.
## Credits
 rmarabini, for https://github.com/rmarabini/chessnutair \
 Graham O'Neil, for the instruction how the board works (pdf) \
 scid-project, for some files we borrowed \
 picochess-project, for inspiration \
 Willi G, for quality management and helping with the code
 

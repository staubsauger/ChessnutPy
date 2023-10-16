# chessnutair
This is a program written in Python. You can connect your Chessnut Air eboard to your pc and play against chess engines.
At the moment we only support the Chessnut Air eboard and only via bluetooth. We tested the program with stockfish and 
the texel chess engines. Both work as intended so we can say, that all uci engines should work. Also the emulation of 
old chesscomputer via mame works, only the takeback function does not work at the moment. 

 * Supports Windows 10 (should work, but not tested)
 * Supports Linux distributions with BlueZ >= 5.43 (See Linux backend for more details)
 * OS X/macOS support (should work, but not tested)

 * we tested this software on a Chessnut Air. As far as we know, it should work on a Chessnut Pro and a Chessnut Air+ too (Please let us know!). 

So far, I have only tested this software on Linux.

## Main Ideas | How it is different to Picochess
The main idea behind this project is to bring a modern solution for people, who want to play chess against the computer, 
but without the distraction of displays, sounds and other things.
This software fits perfect on a small soc like the raspberry pi zero 2. It is intended to be used without a display. 
Everything you need, for setting up a game, is done via the pieces and leds on the board. Furthermore, you can use both 
buttons on the board for setting up a position or restarting a game. At the moment, there is now way to set up the strength
of the engines via the board. You have to use the config file for this.

## Installation and execution
 1. download code
 2. install dependencies (pip3 install -r requirements.txt)
 3. Optional: copy Docs/default.config to your $HOME/.config/chessnutair.config and edit it to your liking
 4. Execute python3 ./main.py
 5. You need stockfish installed on your system. If stockfish is not globaly available on your system, e.g. you compiled it yourself, you have to configure stockfish in you config
 

## Features
 1. Fix-board function: checks if the state of the board is valid and gives you hints, where pieces are wrong and 
 where to put them
 2. If the board is correct, both squares with kings are blinking (there is also a short animation, pointing the direction of the kings). You can now pick a color by "hovering" a king (picking it 
 up and putting it back where it stood)
 3. While ingame, you can hover your own king to get a hint for you next move. This is read out of the opening book 
 (.bin file) which you can configure in your own configuration. If no move was found in the opening book, you get a 
 suggestion from the suggestionengine which you can also configure in your config. Default is stockfish.
 4. If you hover the opponents king, while a game is running, you get the score relative to white, indicated by the leds
 on the board.
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
 

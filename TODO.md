# Webinterface
* Better LiChess integration
    * Chat
    * allow offer Draw/Resign
    * allow Selecting roundlength etc
* Styling
* Make all configuration options available (and write them to ~/.config/chessnutair.config)

# Engine interface
* allow forcing the engine to make Book moves
* allow engine presets (maybe as files, how does picochess do it?)

# Base
* don't use the "root" logger so we dont see aiohttp messages on loglevel info (afterwards maybe also add more info logs)
* configwriter
* rewrite BoardGame to use a statemachine
* enhance drag-support (ideally so it can be on by default)
* propagate settings object instead of individual setting
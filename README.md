A simple and *compact* MicroPython Driver for the Microchip MCP23017.

The core idea behind mpy_mcp23017 is to leverage inheritance to yield the smallest possible footprint on the target - which may have a very modest amount of flash storage.  In other words, if you don't need features, you only deploy whichever parent of the MPY_MCP23017 object that satisfies your needs - eliminating code bloat and source file editing.  At the moment there's only a base version for applications which rely on port polling, and a child component which incorporates interrupt handling, though I envisage extending this as practical needs develop.

I will get around to packaging when the codebase has matured a bit.

My sole target architecture at the moment is ESP32, but it should be trivial to port to other MicroPython implementations.

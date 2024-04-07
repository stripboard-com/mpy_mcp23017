from time import sleep_ms
from machine import Pin

# Frequently used Mode 1 values
IODIRA   = 0x00  # Pin direction registers
IODIRB   = 0x10
PORTA    = 0x00  # don't confuse these logical values with the physical GPIO port locations!
PORTB    = 0x10
GPIOA    = 0x09  # physical locations
GPIOB    = 0x19
# other mode 1 registers
IPOLA    = 0x01
GPINTENA = 0x02
DEFVALA  = 0x03
INTCONA  = 0x04
IOCON    = 0x05
GPPUA    = 0x06
INTFA    = 0x07
INTCAPA  = 0x08
OLATA    = 0x0a
IPOLB    = 0x11
GPINTENB = 0x12
DEFVALB  = 0x13
INTCONB  = 0x14
IOCON    = 0x15  # yes, a duplicate!  So's not to have to test for IOCON
GPPUB    = 0x16
INTFB    = 0x17
INTCAPB  = 0x18
OLATB    = 0x1a

CTL_REG_BANK_0 = [
    'IODIRA', 'IODIRB', 'IPOLA', 'IPOLB', 'GPINTENA', 'GPINTENB', 'DEFVALA', 'DEFVALB',
    'INTCONA', 'INTCONB', 'IOCON', 'IOCON', 'GPPUA', 'GPPUB', 'INTFA', 'INTFB',
    'INTCAPA', 'INTCAPB', 'GPIOA', 'GPIOB', 'OLATA', 'OLATB', ]
# We aren't actually using BANK0 now so above can be deleted to save filespace.

CTL_REG_BANK_1 = [
    'IODIRA', 'IPOLA', 'GPINTENA', 'DEFVALA', 'INTCONA',  'IOCON', 'GPPUA', 'INTFA',
    'INTCAPA', 'GPIOA', 'OLATA', '-', '-', '-', '-', '-',    
    'IODIRB', 'IPOLB', 'GPINTENB', 'DEFVALB', 'INTCONB','IOCON', 'GPPUB', 'INTFB',
    'INTCAPB', 'GPIOB', 'OLATB', ]

# Pin Masks for programming unitary pins
PIN0 = 0x01
PIN1 = 0x02
PIN2 = 0x04
PIN3 = 0x08
PIN4 = 0x10
PIN5 = 0x20
PIN6 = 0x40
PIN7 = 0x80

# sugar
HIGH = 0xff
LOW = 0x00
INPUT = 0xff
OUTPUT = 0x00


class MCP23017:
    """
    A simple and compact Micropython ESP32 Driver for the Microchip MCP23017
    
    IOCON (0x0a) = BANK | MIRROR | SEQOP  | DISSLW | HAEN | ODR | INTPOL | - |
    Pass in a pre-existing I2C object reference (which could be shared with another chip).

    """
        
    def __init__(self, i2c_obj, i2c_addr=0x20, *, respin=0 ):
        """
        First pass in a pre-initialised I2C object (because there may be other devices sharing it).
        The other paramaters are optional, though respin must be a named argument to avoid
        confusion.
        """
        self.i2c = i2c_obj
        self.ic_addr = i2c_addr                             # ic address on bus (a function of device & not bus object)
        # reset the chip  (ensures it's in mode 0 so's we know where ICON can be found)
        if respin < 1:
            i2c_res = Pin( respin, Pin.OUT, value=0)
            sleep_ms(10)
            i2c_res(1)                                          # reset is actually /rst i.e. MUST be set normally high
            sleep_ms(10)
        # now we can safely configure in in mode 1 
        self._mode = 1
        iocon = self.read_reg( 0x0a)                        # IOCON read-modify-write must assume mode 0
        self.write_reg( register=0xa, value= iocon | 0xa0)  # hit BANK and SEQOP flags to stop address increments
        # everything now in bank 1 with no hairy incrementing or toggling going on
        
## Utility Methods ##

    def regstr_to_byte(self, regstr ) -> int:
        """
        General string to register number lookup. Whe don't actually use Bank 0 values here, so they could
        all be eliminated (above) for code compaction.  Ditto this method, if not used.
        """
        if self._mode == 0:
            self.regs = CTL_REG_BANK_0
        else:
            self.regs = CTL_REG_BANK_1
        for self.reg in self.regs:    # registers according to mode
            try:
                byte = self.regs.index(regstr)
            except ValueError:
                import sys
                sys.print_exception(ValueError)   # doesn't actually seeem to open a file on current port
                sys.stderr.write("regstr_to_byte(): unknown register!\n")
                return -1
            return byte	              # int representing byte
        
    def _register_bit(self, pin_mask, reg, state=LOW):
        """
        Sets a individual bit of specified register.
        Returns pin_mask of 0 on failure
        """
        if reg <= OLATB:     # last register of BANK1
            self.oldval = self.read_reg( reg)
            if state == LOW:
                self.newval = self.oldval & (pin_mask ^ 0xff)   # because ~pin_mask sign extends!!!
            else:
                self.newval = self.oldval | pin_mask
            self.write_reg( reg, self.newval)
        else:
            sys.stderr.write("_register_bit(): invalid register\n")
        return pin_mask
        
## Byte-wide Methods ##
    
    def write_reg(self, register, value):
        i2c.writeto( self.ic_addr, bytearray([register, value]) )
        
    def read_reg(self, register) -> int:
        rval_arry = bytearray(b'')
        rval_arry =  self.i2c.readfrom_mem( self.ic_addr, register, 1 )
        return rval_arry[0]
        
    def set_all_output(self):
        """ sets all GPIOs as OUTPUT"""
        self.write_reg( register=0x0, value=OUTPUT)
        if self._mode == 0:
            self.write_reg( register=0x1, value=OUTPUT)
        else:
            self.write_reg( register=0x10, value=OUTPUT)
            
    def set_all_input(self):
        """ sets all GPIOs as INPUT"""
        self.write_reg( register=0x0, value=INPUT)
        if self._mode == 0:
            self.write_reg( register=0x1, value=INPUT)
        else:
            self.write_reg( register=0x10, value=OUTPUT)
            
## Individual Pin Methods ##

    def pin_mode(self, pin_mask, port, state=OUTPUT):
        """
        Sets a individual pin(s) to either INPUT or OUTPUT (default output)
        Returns pin_mask because it might be useful to store this value for
        later use.
        Usage: <ic>.pin_mode( GPB6 | GPB7, GPIOA, mode=INPUT) i.e. or the pin
        values in the first parameter - which you CAN'T mix between ports.
        """
        if port == GPIOA or port == GPIOB:
            self.oldval = self.read_reg( port-GPIOA)
            if state == OUTPUT:
                self.newval = self.oldval & (pin_mask ^ 0xff)     # because ~pin_mask sign extends!!!
            else:
                self.newval = self.oldval | pin_mask
                self.write_reg( (port-GPIOA), self.newval)
        else:
            sys.stderr.write("pin_mode(): must specify GPIOA or GPIOB!\n")
        return pin_mask
        
## Interrupt Methods ##


     def set_interrupt(self, gpio, enabled):
         _register_bit(self, pin_mask, reg, state=LOW)
# 
#     def set_interrupt_mirror(self, enable):
#
#
#     def read_interrupt_captures(self):
#
#
#     def _get_list_of_interrupted_values_from(self, offset):
#
# 
#     def read_interrupt_flags(self):
#         
# 
#     

###            <--- CUT ON THIS LINE to remove surplus code --->

## Debug Methods ##

    def prnregs(self):
        if self._mode == 0:
            self.regs = CTL_REG_BANK_0
        else:
            self.regs = CTL_REG_BANK_1
        print('-'*20)
        for self.reg in self.regs:    # registers according to mode
            if self.reg == '-':
                continue
            reg_byte = self.regs.index(self.reg)
            print( "{} = {}".format( self.reg, hex(self.read_reg(reg_byte)) ) )
        print('-'*20)

          
if __name__ == "__main__":
    print("Demonstrating: mpy_mcp23017.py\n")
    import machine
   
    i2c = machine.I2C(0, scl=22,sda=21)    # possibly a shared object (one per physical I2C)
    ic1 = MCP23017(i2c, 0x20)              # ic could be a schematic/PCB reference
    ic2 = MCP23017(i2c, 0x21, respin=19)   # ALWAYS reset the LAST created device before ops

    ic1.set_all_output()
    ic2.set_all_output()

    ic1.write_reg( register=GPIOA, value=0x76 )
    ic2.write_reg( register=GPIOA, value=0x42 )
    ic1.write_reg( register=ic1.regstr_to_byte("GPIOB"), value=0x52 )  # alternatice write syntax
    ic2.write_reg( register=ic2.regstr_to_byte("GPIOB"), value=0x47 )

    ic1.prnregs()
    
    ic2.pin_mode(PIN7, GPIOA, INPUT)
    sleep_ms(500)
    ic2.pin_mode(PIN7, GPIOA, OUTPUT)
    
# running LED test on both ports
    for p in range(8):
        st = True
        for _ in range(20):
            sleep_ms(100)
            ic2._register_bit( 1<<p, GPIOA, st)
            ic2._register_bit( 1<<p, GPIOB, not st)
            st =  not st
    
    ic2.prnregs()
    
#   ic1.set_all_input()











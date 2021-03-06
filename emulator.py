from unicorn import *
from unicorn.arm_const import *
from logging import *
import hooks
import time
import os

DEFAULT_BASE = 0x400000

STACK_SIZE = 64 * 1024 * 1024  # I don't think we'll ever need more than 64 MB for the stack
BIN_SIZE   = 128 * 1024 * 1024 # allocate 128 MB for the binary, probably overkill

DUMP_DIR = "dump"

class Emulator():
    def __init__(self, base=DEFAULT_BASE):
        self.base = base
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.next_alloc_base = self.base

        self.bin_base = self.alloc(BIN_SIZE)

        self.stack_base = self.alloc(STACK_SIZE)
        self.uc.reg_write(UC_ARM_REG_SP, self.stack_base  + (STACK_SIZE // 2)) # point SP to the middle of the stack, just to be safe

        hooks.register(self)

    def start(self, start_address, end_address):
        log("Emulation starting at {:#010x} with base {:#010x}".format(start_address, self.base))

        linc()
        self.uc.reg_write(UC_ARM_REG_PC, start_address)
        self.uc.emu_start(start_address, end_address)
        log("Emulation ended")
        self.debug_dump()
        ldec()


    def stop(self):
        log("Emulation stopping unexpectedly, PC at {:#010x}".format(self.uc.reg_read(UC_ARM_REG_PC)))

        self.uc.emu_stop()

    def alloc(self, size):
        alloc_base = self.next_alloc_base
        self.uc.mem_map(self.next_alloc_base, size)
        self.next_alloc_base += size
        return alloc_base

    def allocations(self):
        return [reg for reg in self.uc.mem_regions()]

    def read_string(self, address):
        buf = []
        while True:
            c = self.uc.mem_read(address, 1)[0]
            if c == 0: # strings end with a null terminator
                break
            buf.append(c)
            address += 1
        return "".join(map(chr, buf))

    def debug_dump(self):
        local_dir = os.path.dirname(__file__)
        out_dir = os.path.join(local_dir, DUMP_DIR, str(int(time.time())))
        os.makedirs(out_dir)
        
        for begin, end, prot in self.allocations():
            filename = "{:#010x}-{:#010x}.bin".format(begin, end)
            pathname = os.path.join(out_dir, filename)
            with open(pathname, "wb") as f:
                f.write(self.uc.mem_read(begin, end - begin))
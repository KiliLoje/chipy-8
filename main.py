import random import sys
import pyray as rl


FLAG_REGISTER = 0xF


class Code:
    def __init__(self, i):
        self.raw = i
        self.category = (i & 0xF000) >> 0xC
        self.x = (i & 0x0F00) >> 0x8
        self.y = (i & 0x00F0) >> 0x4
        self.n1 = i & 0x000F
        self.n2 = i & 0x00FF
        self.n3 = i & 0x0FFF


class Chip8:
    def __init__(self) -> None:
        self.opt_superchip = False

        self.ram = bytearray([0] * 4096)

        # Font initialization
        self.ram[0x50:0x9F] = [
            0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
            0x20, 0x60, 0x20, 0x20, 0x70,  # 1
            0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
            0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
            0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
            0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
            0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
            0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
            0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
            0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
            0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
            0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
            0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
            0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
            0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
            0xF0, 0x80, 0xF0, 0x80, 0x80,  # F
        ]

        # Here we use a boolean list for ease of understanding.
        # Each Pixel is either
        # True : white
        # False : black
        self.screen = [False] * 64 * 32
        self.inputs = [False] * 16

        self.stack = []

        self.delay_timer = 0
        self.sound_timer = 0

        self.pc = 0  # program counter (instruction pointer)
        self.i = 0  # index register

        # global registers
        self.v = [0] * 16

        self.current_instruction = self.cls

    def load_program(self, path):
        with open(path, "rb") as b:
            rom = b.read()
        self.ram[0x200 : 0x200 + len(rom)] = rom
        self.pc = 0x200

    def fetch(self):
        code = (self.ram[self.pc] << 8) + self.ram[self.pc + 1]
        self.pc += 2
        self.current_code = Code(code)

    def decode(self):
        c = self.current_code
        self.current_instruction = self.nop

        match c.category:
            case 0:
                if c.raw == 0x00E0:
                    self.current_instruction = self.cls
                elif c.raw == 0x00EE:
                    self.current_instruction = self.sub_ret
            case 1:
                self.current_instruction = self.jmp
            case 2:
                self.current_instruction = self.sub_jmp
            case 3:
                self.current_instruction = self.eq_skip
            case 4:
                self.current_instruction = self.neq_skip
            case 5:
                self.current_instruction = self.reg_eq_skip
            case 9:
                self.current_instruction = self.reg_neq_skip
            case 6:
                self.current_instruction = self.set
            case 7:
                self.current_instruction = self.add
            case 8:
                match c.n1:
                    case 0:
                        self.current_instruction = self.set_reg
                    case 1:
                        self.current_instruction = self.or_reg
                    case 2:
                        self.current_instruction = self.and_reg
                    case 3:
                        self.current_instruction = self.xor_reg
                    case 4:
                        self.current_instruction = self.add_reg
                    case 5:
                        self.current_instruction = self.sub_reg_xy
                    case 7:
                        self.current_instruction = self.sub_reg_yx
                    case 6:
                        self.current_instruction = self.r_shift
                    case 0xE:
                        self.current_instruction = self.l_shift
            case 0xA:
                self.current_instruction = self.set_i
            case 0xB:
                self.current_instruction = self.offset_jmp
            case 0xC:
                self.current_instruction = self.rand
            case 0xD:
                self.current_instruction = self.display
            case 0xE:
                match c.n2:
                    case 0x9E:
                        self.current_instruction = self.skip_if_input_pressed
                    case 0xA1:
                        self.current_instruction = self.skip_if_input_not_pressed
            case 0xF:
                match c.n2:
                    case 0x07:
                        self.current_instruction = self.get_delay
                    case 0x15:
                        self.current_instruction = self.set_delay
                    case 0x18:
                        self.current_instruction = self.set_sound
                    case 0x1E:
                        self.current_instruction = self.add_i
                    case 0x0A:
                        self.current_instruction = self.get_key
                    case 0x29:
                        self.current_instruction = self.font_char
                    case 0x33:
                        self.current_instruction = self.bcd_store
                    case 0x55:
                        self.current_instruction = self.store
                    case 0x65:
                        self.current_instruction = self.load

    def execute(self):
        self.current_instruction()

    def vx(self):
        return self.v[self.current_code.x]

    def vy(self):
        return self.v[self.current_code.y]

    def nop(self):
        pass

    def cls(self):
        self.screen = [0] * 64 * 32

    def jmp(self):
        self.pc = self.current_code.n3

    def sub_jmp(self):
        self.stack.append(self.pc)
        self.pc = self.current_code.n3

    def sub_ret(self):
        self.pc = self.stack[-1]
        self.stack.pop()

    def eq_skip(self):
        if self.vx() == self.current_code.n2:
            self.pc += 2

    def neq_skip(self):
        if self.vx() != self.current_code.n2:
            self.pc += 2

    def reg_eq_skip(self):
        if self.vx() == self.vy():
            self.pc += 2

    def reg_neq_skip(self):
        if self.vx() != self.vy():
            self.pc += 2

    def set(self):
        self.v[self.current_code.x] = self.current_code.n2

    def add(self):
        self.v[self.current_code.x] = (self.vx() + self.current_code.n2) % 0x100

    def set_reg(self):
        self.v[self.current_code.x] = self.vy()

    def or_reg(self):
        self.v[self.current_code.x] = (self.vx() | self.vy()) % 0x100

    def and_reg(self):
        self.v[self.current_code.x] = (self.vx() & self.vy()) % 0x100

    def xor_reg(self):
        self.v[self.current_code.x] = (self.vx() ^ self.vy()) % 0x100

    def add_reg(self):
        vx = self.vx() + self.vy()
        if vx > 255:
            vx %= 256
            carry = 1
        else:
            carry = 0
        self.v[self.current_code.x] = vx
        self.v[FLAG_REGISTER] = carry

    def sub_reg_xy(self):
        vx = self.vx()
        vy = self.vy()
        if vx >= vy:
            self.v[self.current_code.x] = vx - vy
            self.v[FLAG_REGISTER] = 1
        else:
            self.v[self.current_code.x] = (0x100 - vy + vx) % 0x100
            self.v[FLAG_REGISTER] = 0

    def sub_reg_yx(self):
        vx = self.vx()
        vy = self.vy()
        if vy >= vx:
            self.v[self.current_code.x] = vy - vx
            self.v[FLAG_REGISTER] = 1
        else:
            self.v[self.current_code.x] = (0x100 - vx + vy) % 0x100
            self.v[FLAG_REGISTER] = 0

    def r_shift(self):
        if not self.opt_superchip:
            self.v[self.current_code.x] = self.vy()
        carry = (self.vx() & 0b00000001) == 1
        self.v[self.current_code.x] >>= 1
        self.v[FLAG_REGISTER] = carry

    def l_shift(self):
        if not self.opt_superchip:
            self.v[self.current_code.x] = self.vy()
        carry = (self.vx() & 0b10000000) == 1
        self.v[self.current_code.x] = (self.vx() << 1) % 0x100
        self.v[FLAG_REGISTER] = carry

    def set_i(self):
        self.i = self.current_code.n3

    def offset_jmp(self):
        self.pc = self.current_code.n3
        if self.opt_superchip:
            self.pc += self.vx()
        else:
            self.pc += self.v[0]

    def rand(self):
        self.v[self.current_code.x] = random.randrange(0, 256) & self.current_code.n2

    def display(self):
        c = self.current_code
        x_pos = self.v[c.x] % 64
        y_pos = self.v[c.y] % 32
        self.v[FLAG_REGISTER] = 0
        for row in range(c.n1):
            current_byte = self.ram[self.i + row]
            for bit in range(8):
                if current_byte & (0x80 >> bit):
                    px = (x_pos + bit) % 64
                    py = (y_pos + row) % 32
                    idx = py * 64 + px
                    if self.screen[idx]:
                        self.v[FLAG_REGISTER] = 1
                    self.screen[idx] ^= 1

    def skip_if_input_pressed(self):
        if self.inputs[self.vx()]:
            self.pc += 2

    def skip_if_input_not_pressed(self):
        if not self.inputs[self.vx()]:
            self.pc += 2

    def get_delay(self):
        self.v[self.current_code.x] = self.delay_timer

    def set_delay(self):
        self.delay_timer = self.vx()

    def set_sound(self):
        self.sound_timer = self.vx()

    def add_i(self):
        self.i += self.vx()

    def get_key(self):
        for i in range(len(self.inputs)):
            if self.inputs[i]:
                self.v[self.current_code.x] = i
                return
        self.pc -= 2

    def font_char(self):
        if self.vx() <= 0xF and self.vx() >= 0:
            self.i = 0x50 + (0x5 * self.vx())

    def bcd_store(self):
        self.ram[self.i] = self.vx() // 100
        self.ram[self.i + 1] = (self.vx() % 100) // 10
        self.ram[self.i + 2] = self.vx() % 10

    def store(self):
        for i in range(self.current_code.x + 1):
            self.ram[self.i + i] = self.v[i]
        if not self.opt_superchip:
            self.i += self.current_code.x + 1

    def load(self):
        for i in range(self.current_code.x + 1):
            self.v[i] = self.ram[self.i + i]
        if not self.opt_superchip:
            self.i += self.current_code.x + 1


chip = Chip8()
chip.load_program(sys.argv[1])
chip.opt_superchip = True


def get_inputs():
    keycodes = [
        rl.KeyboardKey.KEY_ONE,
        rl.KeyboardKey.KEY_TWO,
        rl.KeyboardKey.KEY_THREE,
        rl.KeyboardKey.KEY_FOUR,
        rl.KeyboardKey.KEY_Q,
        rl.KeyboardKey.KEY_W,
        rl.KeyboardKey.KEY_E,
        rl.KeyboardKey.KEY_R,
        rl.KeyboardKey.KEY_A,
        rl.KeyboardKey.KEY_S,
        rl.KeyboardKey.KEY_D,
        rl.KeyboardKey.KEY_F,
        rl.KeyboardKey.KEY_Z,
        rl.KeyboardKey.KEY_X,
        rl.KeyboardKey.KEY_C,
        rl.KeyboardKey.KEY_V,
    ]
    for i in range(len(chip.inputs)):
        chip.inputs[i] = rl.is_key_down(keycodes[i])


INSTRUCTIONS_PER_SECOND = 700
TIMERS_HZ = 60

cpu_accumulator = 0.0
timer_accumulator = 0.0
debug = False
rl.init_window(640, 320, "chipy8")

while not rl.window_should_close():
    while debug:
        pass

    dt = rl.get_frame_time()

    cpu_accumulator += dt
    cycle_period = 1.0 / INSTRUCTIONS_PER_SECOND
    while cpu_accumulator >= cycle_period:
        get_inputs()
        chip.fetch()
        chip.decode()
        chip.execute()
        cpu_accumulator -= cycle_period

    timer_accumulator += dt
    timer_period = 1.0 / TIMERS_HZ
    while timer_accumulator >= timer_period:
        if chip.delay_timer != 0:
            chip.delay_timer -= 1
        if chip.sound_timer != 0:
            chip.sound_timer -= 1
        timer_accumulator -= timer_period

    rl.begin_drawing()
    rl.clear_background(rl.BLACK)
    for y in range(32):
        for x in range(64):
            if chip.screen[y * 64 + x]:
                rl.draw_rectangle(x * 10, y * 10, 10, 10, rl.WHITE)
    rl.end_drawing()


rl.close_window()

import machine

# (c) IDWizard 2017
# MIT License.
import time

LOW = 0
HIGH = 1
FULL_ROTATION = int(4075.7728395061727 / 8) # http://www.jangeox.be/2013/10/stepper-motor-28byj-48_25.html

HALF_STEP = [
    [HIGH, LOW, LOW, LOW],
    [HIGH, HIGH, LOW, LOW],
    [LOW, HIGH, LOW, LOW],
    [LOW, HIGH, HIGH, LOW],
    [LOW, LOW, HIGH, LOW],
    [LOW, LOW, HIGH, HIGH],
    [LOW, LOW, LOW, HIGH],
    [HIGH, LOW, LOW, HIGH],
]

FULL_STEP = [
 [HIGH, HIGH, LOW, LOW],
 [LOW, HIGH, HIGH, LOW],
 [LOW, LOW, HIGH, HIGH],
 [HIGH, LOW, LOW, HIGH]
]

class Command():
    """Tell a stepper to move X many steps in direction"""
    def __init__(self, stepper, steps, direction=1):
        self.stepper = stepper
        self.steps = steps
        self.direction = direction

class Driver():
    """Drive a set of motors, each with their own commands"""

    @staticmethod
    def run(commands):
        """Takes a list of commands and interleaves their step calls"""
        
        # Work out total steps to take
        max_steps = sum([c.steps for c in commands])

        count = 0
        while count != max_steps:
            for command in commands:
                # we want to interleave the commands
                if command.steps > 0:
                    command.stepper.step(1, command.direction)
                    command.steps -= 1
                    count += 1
        
class Stepper():
    def __init__(self, mode, pin1, pin2, pin3, pin4, delay=7500):
        self.mode = mode
        self.pin1 = machine.Pin(pin1, machine.Pin.OUT)
        self.pin2 = machine.Pin(pin2, machine.Pin.OUT)
        self.pin3 = machine.Pin(pin3, machine.Pin.OUT)
        self.pin4 = machine.Pin(pin4, machine.Pin.OUT)
        self.delay = delay  # Recommend 10+ for FULL_STEP, 1 is OK for HALF_STEP
        
        # Initialize all to 0
        self.reset()
        
    def step(self, count, direction=1):
        """Rotate count steps. direction = -1 means backwards"""
        for x in range(count):
            for bit in self.mode[::direction]:
                self.pin1.value(bit[0]) 
                self.pin2.value(bit[1]) 
                self.pin3.value(bit[2]) 
                self.pin4.value(bit[3]) 
                time.sleep_us(self.delay)

        self.reset()
        
    def reset(self):
        # Reset to 0, no holding, these are geared, you can't move them
        self.pin1.value(0) 
        self.pin2.value(0) 
        self.pin3.value(0) 
        self.pin4.value(0) 

if __name__ == '__main__':
    pass
    #s1 = Stepper(HALF_STEP, microbit.pin16, microbit.pin15, microbit.pin14, microbit.pin13, delay=5)    
    #s2 = Stepper(HALF_STEP, microbit.pin6, microbit.pin5, microbit.pin4, microbit.pin3, delay=5)   
    #s1.step(FULL_ROTATION)
    #s2.step(FULL_ROTATION)

    #runner = Driver()
    #runner.run([Command(s1, FULL_ROTATION, 1), Command(s2, FULL_ROTATION/2, -1)])

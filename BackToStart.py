from platform import system
import pygame as pg
import random
import json
import os

import utils

# Init
pg.init()


# Main class
class Game:
    def __init__(self, win_size):
        # Create window
        self.win_size = win_size
        self.win = pg.display.set_mode(win_size)
        pg.display.set_caption('Back To Start')
        pg.display.set_icon(pg.image.load('res/gfx/icon.png'))

        # Clock to keep track of time
        self.clock = pg.time.Clock()

        self.on_init()

    def on_init(self):
        # Initialize resource dicts
        self.gfx: dict[pg.Surface] = {}
        self.sfx: dict[pg.mixer.Sound] = {}

        # Detect platform and assign settings path depending on which os ur using
        if system().lower() == 'linux':
            self.sett_file = os.path.expanduser('~/.local/share/backtostart.bin')
        elif system().lower() == 'windows':
            self.sett_file = os.path.expanduser('~/AppData/Roaming/backtostart.bin')
        elif system().lower() == 'darwin': # macOS support added untested (i don't want to sell my kidney yet) - please report if broken!
            self.sett_file = os.path.expanduser('~/Library/Application Support/backtostart.bin')
        else:
            self.sett_file = None
            print('Your OS wasn\'t recognized! Your settings won\'t be saved')

        # Initialize variables
        self.game_started = False
        self.show_menu = False
        self.can_jump = False
        self.paused = False
        self.dead = False
        self.framerate = 60
        self.bounce_x = 64
        self.counter = 180
        self.gravity = -.6
        self.screen = 0
        self.timer = 0
        self.score = 0
        self.speed = 4
        self.vel_y = 0
        self.dir = 0
        self.particles: list[Particle] = []
        self.size = (15*4, 12*4)
        self.pos = [self.win_size[0]//2, self.win_size[1]-260]

        # Create the menu GUI using [slicing](https://en.wikipedia.org/wiki/9-slice_scaling)
        self.menu = utils.load_img(utils.get_slice(42, 26, pg.image.load('res/gfx/gui/gui.png')))

        # Load levels
        w, h = self.win_size
        with open('levels.json', 'r') as f:
            levels = json.load(f)
            self.levels = []
            for level in levels:
                a = []
                for rect in level:
                    a.append(Platform((rect[0], rect[1]), (rect[2], rect[3]), rect[4]))
                self.levels.append(a)
        self.level = random.choice(self.levels)

        # Load settings
        if self.sett_file:
            # If file doesn't exist, create a new one
            if not os.path.exists(self.sett_file):
                with open(self.sett_file, 'wb') as f: f.write(bytes([0b00000110]))
            with open(self.sett_file, 'rb') as f:
                sett = ord(f.read(1))
                self.seen_welcome = bool((sett>>4)&0b1)
                self.seen_tutorial = bool((sett>>3)&0b1)
                self.music_on = bool((sett>>2)&0b1)
                self.sfx_on = bool((sett>>1)&0b1)
                self.hitbox = bool(sett&0b1)

        self.load_resources()

        self.welcome_pos = ((self.win_size[0]-self.gfx['welcome'].get_size()[0])//2, 128)

    def run(self):
        # Mainloop
        while True:
            self.events() # Handle events like window closing or user input
            self.tick() # Calculate everything
            self.render() # Draw everything onto the screen

    def events(self):
        for e in pg.event.get():
            # Exit if window closed
            if e.type == pg.QUIT:
                pg.quit()
                raise SystemExit(0)

            # If key pressed down...
            if e.type == pg.KEYDOWN:
                # ... and the game didn't start and [<] is pressed ...
                if e.key in [pg.K_LEFT, pg.K_a] and not self.game_started:
                    # ... start the game, music (if music is on) and start moving the player to the left
                    self.game_started = True
                    self.start_time = pg.time.get_ticks()
                    self.dir = -1
                    if self.music_on: self.sfx['music'].play(-1)
                # ... and the game didn't start and [>] is pressed ...
                if e.key in [pg.K_RIGHT, pg.K_d] and not self.game_started:
                    # ... start the game, music (if music is on) and start moving the player to the right
                    self.game_started = True
                    self.start_time = pg.time.get_ticks()
                    self.dir = 1
                    if self.music_on: self.sfx['music'].play(-1)
                # ... and [  ---  ] or [^] pressed and game started and you can jump (on ground) ...
                if e.key in [pg.K_SPACE, pg.K_UP, pg.K_w] and self.game_started and self.can_jump:
                    # ... jump and play sound of jump
                    self.vel_y = 12
                    if self.sfx_on: self.sfx['jump'].play()

                # pause
                if e.key == pg.K_ESCAPE:
                    if self.paused:
                        pg.mixer.unpause()
                    else:
                        pg.mixer.pause()
                    self.paused = not self.paused

                # if any key pressed, hide the menu
                self.show_menu = False

            # If mouse clicked...
            mpos = pg.mouse.get_pos() # get mouse coordinates
            if e.type == pg.MOUSEBUTTONDOWN:
                if pg.Rect(12,12,44,44).collidepoint(mpos): # and mouse touching menu button
                    # toggle menu vissible
                    self.show_menu = not self.show_menu

                elif self.show_menu: # if menu visible
                    # ... and mouse pressed on music checkbox
                    if pg.Rect(24, 80, 36, 36).collidepoint(mpos):
                        # toggle music
                        self.music_on = not self.music_on

                    # ... and mouse pressed on sound effects checkbox
                    if pg.Rect(24, 124, 36, 36).collidepoint(mpos):
                        # toggle sfx
                        self.sfx_on = not self.sfx_on

                    # Save settings
                    if self.sett_file:
                        # open settings file
                        with open(self.sett_file, 'wb') as f:
                            # write settings into a single byte
                            sett_byte = (int(self.seen_welcome)<<4) | (int(self.seen_tutorial)<<3) | (int(self.music_on)<<2) | (int(self.sfx_on)<<1) | int(self.hitbox)

                            # and write to the file
                            f.write(bytes([sett_byte]))
            
            if e.type == pg.MOUSEBUTTONUP:
                if pg.Rect(self.welcome_pos[0]+32, self.welcome_pos[1]+412, 132, 68).collidepoint(mpos) and not self.seen_welcome:
                    self.seen_welcome = True
                    if self.sett_file:
                        with open(self.sett_file, 'wb') as f:
                            sett_byte = (int(self.seen_welcome)<<4) | (int(self.seen_tutorial)<<3) | (int(self.music_on)<<2) | (int(self.sfx_on)<<1) | int(self.hitbox)
                            f.write(bytes([sett_byte]))
                if self.paused:
                    bx = (self.win_size[0]-192)//2
                    if pg.Rect(bx, 320, 192, 60).collidepoint(mpos):
                        # Resume
                        self.paused = False
                        pg.mixer.unpause()
                        
                    if pg.Rect(bx, 400, 192, 60).collidepoint(mpos):
                        # Reset
                        self.game_started = False
                        self.paused = False
                        self.counter = 180
                        self.screen = 0
                        self.timer = 0
                        self.score = 0
                        self.dir = 0
                        self.pos = [self.win_size[0]//2, self.win_size[1]-260]
                        self.sfx['music'].stop()

                    if pg.Rect(bx, 480, 192, 60).collidepoint(mpos):
                        # Quit
                        pg.event.post(pg.event.Event(pg.QUIT))

    def tick(self): # the thing that does everything on every frame
        if self.seen_welcome: self.counter -= 1
        self.clock.tick(self.framerate)

        # if player ded
        if self.dead:
            # TODO: Play some animation (prob will never do that)
            # if counter reached 0
            if self.counter == 0:
                # reset game (move to start, disable the `ded` flag, change screen to main menu)
                self.game_started = False
                self.dead = False
                self.screen = 0
                self.counter = 2147483647
                self.pos = [self.win_size[0]//2, self.win_size[1]-260]
                self.level = random.choice(self.levels)
        
        # if player not ded
        elif not self.paused:

            # Get current position and size as smaller variables for convenience
            x, y = self.pos
            self.vel_y += self.gravity
            dx = self.dir * self.speed
            dy = self.vel_y
            s=self.size
            hw = s[0]//2 # Half Width
            h = s[1] # Height

            x += dx
            y -= dy

            # Handle different screens
            if self.screen == 0:
                # Simple ground collision for screen 0
                ground_level = self.win_size[1] - 83
                self.can_jump = (y >= ground_level - h)
                
                # if player can jump (which means is on ground)
                if self.can_jump:
                    # move him to the ground level
                    y = ground_level - h
                    self.vel_y = 0
            else:
                # Assume not on ground until we detect a collision
                self.can_jump = False

                # Check vertical collisions against platforms
                for plat in self.level: # loop though every platform in current level
                    rect = plat.get_rect()

                    match plat.type:
                        case 0 | 1: # If is a normal platform
                            # Ok. This will be hard to explain, but i will try my best
                            if rect.colliderect(x-hw, y-h, *self.size):
                                # Check if player hit the side of a platform
                                if y > rect.top+1+abs(self.vel_y) and (x > rect.right+hw-1-dx or x < rect.left-hw+1+dx):
                                    # cancel the movement
                                    x -= dx
                                    dx = 0
                                else:#if didn't hit the side
                                    if dy <= 0:
                                        # On top of platform
                                        y = rect.top + 1
                                        self.can_jump = True
                                    if plat.type == 0 and not rect.colliderect(x-hw, y-h+abs(self.vel_y)+4, *self.size):
                                        # Hit from bottom
                                        y = rect.bottom + h + 1
                                        self.can_jump = False
                                    self.vel_y = 0
                        case 2: # if is a bounce platform
                            if rect.colliderect(x-hw, y-h, *self.size):
                                self.dir = -self.dir

                
                # Check if player is between the side boundaries
                if (x < 256 + hw or x > self.win_size[0] - 256 - hw) and not self.can_jump:
                    if y > self.win_size[1] - 83 - h:
                        y = self.win_size[1] - 83 - h
                        self.can_jump = True
                        if self.vel_y < -20:
                            for i in range(7):
                                vel = [random.randint(-50, 50)/25, -(random.randint(100, 120)/20)]
                                duration = random.randint(72, 240)
                                self.particles.append(Particle([x, y], vel, self.screen, duration, self.win_size[1]))
                        self.vel_y = 0
                    else:
                        self.can_jump = False

            # Check screen edges
            match self.screen:
                case -1:
                    if x > self.win_size[0]:
                        self.screen = 1
                        x = 0
                        self.level = random.choice(self.levels)
                    elif x-hw <= self.bounce_x+4:
                        self.dir = -self.dir
                        self.score += 1
                case 0:
                    if x < 0:
                        self.screen = -1
                        x = self.win_size[0]
                    elif x > self.win_size[0]:
                        self.screen = 1
                        x = 0
                case 1:
                    if x < 0:
                        self.screen = -1
                        x = self.win_size[0]
                        self.level = random.choice(self.levels)
                    elif x+hw >= self.win_size[0] - self.bounce_x-4:
                        self.dir = -self.dir
                        self.score += 1

            self.pos = [x, y]

            # Check death
            if self.screen in [-1, 1]:
                if y > self.win_size[1]-64:
                    self.sfx['music'].stop()
                    self.dir = 0
                    self.dead = True
                    self.counter = 30
                    self.score = 0

            if self.game_started:
                self.timer += 1
            
        for p in self.particles:
            if p.passed_time > p.dur:
                self.particles.remove(p)
                continue
            p.update()

    def render(self):
        time = pg.time.get_ticks()
        gfx = self.gfx

        # Clear screen
        self.win.fill('#1E1E1E')

        # Draw background
        for x in [0,1,2]:
            for y in [-1,0,1]:
                self.win.blit(gfx['bg_bricks'], (x*512-166-83*self.screen, y*512-96*self.screen))

        # Draw logo & UI
        if self.screen == 0:
            self.win.blit(gfx['logo'], ((self.win_size[0] - gfx['logo'].get_size()[0])//2, 124))
            self.win.blit(gfx['menu_button'].subsurface(44*pg.Rect(12,12,44,44).collidepoint(pg.mouse.get_pos()), 0, 44, 44), (12, 12))
            if self.show_menu:
                self.win.blit(self.menu, (12, 68))
                self.win.blit(gfx['checkbox'].subsurface(36*self.music_on, 0, 36, 36), (24, 80))
                self.win.blit(gfx['checkbox'].subsurface(36*self.sfx_on, 0, 36, 36), (24, 124))
                self.win.blit(gfx['music'], (68, 84))
                self.win.blit(gfx['sfx'], (68, 128))

        # Draw lava
        if self.screen in [-1, 1]:
            for i in range(3):
                self.win.blit(gfx['lava'], ((i-1)*512 + time//25%512, self.win_size[1]-128))

        # Draw Blocks
        if self.screen != 0:
            for plat in self.level:
                rect = plat.get_rect()

                self.win.blit(gfx['bricks'].subsurface(rect[0]%(512-rect[2]), rect[1]%(512-rect[3]), rect[2], rect[3]), (rect[0], rect[1]))
                if plat.type == 0:
                    pg.draw.rect(self.win, '#808080', pg.Rect(rect[0], rect[1], rect[2], rect[3]), 4)
                elif plat.type == 1:
                    pg.draw.rect(self.win, '#808000', pg.Rect(rect[0], rect[1], rect[2], rect[3]), 4)
                elif plat.type == 2:
                    pg.draw.rect(self.win, '#008080', pg.Rect(rect[0], rect[1], rect[2], rect[3]), 4)
                else:
                    raise TypeError('Incorrect platform type!')

                if self.hitbox: pg.draw.rect(self.win, '#ff0000', pg.Rect(rect[0], rect[1], rect[2], rect[3]), 1)

        # Draw walls
        if self.screen == -1:
            self.win.blit(gfx['bricks'], (-512+self.bounce_x, 0))
            self.win.blit(gfx['bricks'], (-512+self.bounce_x, 512))
        elif self.screen == 1:
            self.win.blit(gfx['bricks'], (self.win_size[0]-self.bounce_x, 0))
            self.win.blit(gfx['bricks'], (self.win_size[0]-self.bounce_x, 512))

        # Draw ground
        if self.screen == 0:
            for x in [0,1,2]:
                self.win.blit(gfx['bricks'], (x*512-256, self.win_size[1]-128))
            pg.draw.line(self.win, '#808080', (0, self.win_size[1]-131), (self.win_size[0], self.win_size[1]-131), 4)
        else:
            self.win.blit(gfx['bricks'], (-256, self.win_size[1]-128))
            self.win.blit(gfx['bricks'], (self.win_size[0]-256, self.win_size[1]-128))
            if self.screen == -1:
                pg.draw.lines(self.win, '#808080', False, [(self.bounce_x-3, 0), (self.bounce_x-3, self.win_size[1]-131), (256, self.win_size[1]-131), (256, self.win_size[1])], 4)
                pg.draw.lines(self.win, '#808080', False, [(self.win_size[0], self.win_size[1]-131), (self.win_size[0]-256, self.win_size[1]-131), (self.win_size[0]-256, self.win_size[1])], 4)
            if self.screen == 1:
                pg.draw.lines(self.win, '#808080', False, [(self.win_size[0]-self.bounce_x-3, 0), (self.win_size[0]-self.bounce_x-3, self.win_size[1]-131), (self.win_size[0]-256, self.win_size[1]-131), (self.win_size[0]-256, self.win_size[1])], 4)
                pg.draw.lines(self.win, '#808080', False, [(self.win_size[0]-self.win_size[0], self.win_size[1]-131), (256, self.win_size[1]-131), (256, self.win_size[1])], 4)

            # Fix corners
            pg.draw.line(self.win, '#808080', (self.win_size[0]-257, self.win_size[1]-132), (self.win_size[0]-256, self.win_size[1]-132))
            pg.draw.line(self.win, '#808080', (257, self.win_size[1]-132), (258, self.win_size[1]-132))
            pg.draw.rect(self.win, '#808080', (self.win_size[0]-self.bounce_x-2, self.win_size[1]-130, 2, 2))
            pg.draw.rect(self.win, '#808080', (self.bounce_x-4, self.win_size[1]-130, 2, 2))

        # Draw player
        if self.can_jump:
            self.win.blit(gfx['player'].subsurface((self.dir+1)*72, (time//200%2)*48, 18*4, 12*4), (self.pos[0]-self.size[0]//2-4, self.pos[1]-self.size[1]-1))
        else:
            self.win.blit(gfx['player'].subsurface((self.dir+1)*72, 2*48, 18*4, 12*4), (self.pos[0]-self.size[0]//2-4, self.pos[1]-self.size[1]-1))
        if self.hitbox:
            pg.draw.rect(self.win, '#ff0000', (self.pos[0] - self.size[0]//2, self.pos[1] - self.size[1], *self.size), 1)
            vel = (4*self.dir*self.speed, 4*-self.vel_y)
            pg.draw.line(self.win, '#00ff00', (self.pos[0], self.pos[1]-self.size[1]//2), (self.pos[0]+vel[0], self.pos[1]-self.size[1]//2+vel[1]), 3)
        
        for p in self.particles:
            if p.screen == self.screen:
                self.win.blit(gfx['bricks'].subsurface(p.tex_pos[0], p.tex_pos[1], 8, 8), (p.pos[0]-4, p.pos[1]-4))
                #pg.draw.rect(self.win, '#808080', (p.pos[0]-4, p.pos[1]-4, 8, 8), 2)
                if self.hitbox: pg.draw.rect(self.win, '#ff00ff', (p.pos[0]-4, p.pos[1]-4, 8, 8), 1)

        # Draw timer
        if self.game_started:
            tmp = pg.Surface((156, 48), pg.SRCALPHA)
            pg.draw.rect(tmp, '#ffffff40', (0, 0, 156, 48), 0, -1, -1, -1, 4)
            
            minutes = self.timer//3600
            seconds = int(self.timer//60)%60
            minutes = f'{'0' if minutes < 10 else ''}{minutes}'
            seconds = f'{'0' if seconds < 10 else ''}{seconds}'

            timer = f'{minutes}:{seconds}'
            chars = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':']
            for i, char in enumerate(timer):
                tmp.blit(gfx['digits'].subsurface(20*chars.index(char), 0, 20, 32), ((i+1)*24, 8))

            self.win.blit(tmp, (self.win_size[0]-156, 0))

        # Draw score
        if self.game_started:
            tmp = pg.Surface((96, 48), pg.SRCALPHA)
            pg.draw.rect(tmp, '#ffffff40', (0, 0, 96, 48), 0, -1, -1, -1, 4, 4)

            chars = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':']
            for i, char in enumerate(str(self.score)):
                tmp.blit(gfx['digits'].subsurface(20*chars.index(char), 0, 20, 32), (50+i*24-len(str(self.score))*12, 8))

            self.win.blit(tmp, (self.win_size[0]//2-48, 0))

        # Draw tutuorial
        if not self.seen_tutorial and self.seen_welcome:
            if self.counter < 0 and not self.game_started:
                self.win.blit(gfx['lr_tutorial'], ((self.win_size[0]-gfx['lr_tutorial'].get_size()[0])//2, 24))
            elif -720 < self.counter < 0 and self.game_started:
                self.win.blit(gfx['jump_tutorial'], ((self.win_size[0]-gfx['jump_tutorial'].get_size()[0])//2, 64))
            elif self.game_started and self.counter < -720:
                self.seen_tutorial = True
                if self.sett_file:
                    # open settings file
                    with open(self.sett_file, 'wb') as f:
                        # write settings into a single byte
                        sett_byte = (int(self.seen_welcome)<<4) | (int(self.seen_tutorial)<<3) | (int(self.music_on)<<2) | (int(self.sfx_on)<<1) | int(self.hitbox)

                        # and write to the file
                        f.write(bytes([sett_byte]))

        mpos = pg.mouse.get_pos()
        if not self.seen_welcome:
            welcome_pos = self.welcome_pos
            self.win.blit(gfx['welcome'], welcome_pos)
            self.win.blit(pg.transform.scale_by(gfx['player'].subsurface(72, (time//200%2)*48, 18*4, 12*4), 2), (welcome_pos[0]+572, welcome_pos[1]+40))
            if pg.Rect(welcome_pos[0]+32, welcome_pos[1]+412, 132, 68).collidepoint(mpos):
                if pg.mouse.get_pressed()[0]:
                    self.win.blit(gfx['hide'].subsurface(0, 136, 132, 68), (welcome_pos[0]+32, welcome_pos[1]+412))
                else:
                    self.win.blit(gfx['hide'].subsurface(0, 68, 132, 68), (welcome_pos[0]+32, welcome_pos[1]+412))
            else:
                self.win.blit(gfx['hide'].subsurface(0, 0, 132, 68), (welcome_pos[0]+32, welcome_pos[1]+412))

        if self.paused:
            tmp = pg.Surface(self.win_size, pg.SRCALPHA)
            tmp.fill((0, 0, 0, 64))
            self.win.blit(tmp, (0, 0))

            self.win.blit(gfx['paused'], ((self.win_size[0]-gfx['paused'].get_size()[0])//2, 240))

            bx = (self.win_size[0]-192)//2
            # Resume
            if pg.Rect(bx, 320, 192, 60).collidepoint(mpos):
                if pg.mouse.get_pressed()[0]:
                    self.win.blit(gfx['resume'].subsurface(0, 120, 192, 60), (bx, 320))
                else:
                    self.win.blit(gfx['resume'].subsurface(0, 60, 192, 60), (bx, 320))
            else:
                self.win.blit(gfx['resume'].subsurface(0, 0, 192, 60), (bx, 320))
            
            # Reset
            if pg.Rect(bx, 400, 192, 60).collidepoint(mpos):
                if pg.mouse.get_pressed()[0]:
                    self.win.blit(gfx['reset'].subsurface(0, 120, 192, 60), (bx, 400))
                else:
                    self.win.blit(gfx['reset'].subsurface(0, 60, 192, 60), (bx, 400))
            else:
                self.win.blit(gfx['reset'].subsurface(0, 0, 192, 60), (bx, 400))

            # Quit
            if pg.Rect(bx, 480, 192, 60).collidepoint(mpos):
                if pg.mouse.get_pressed()[0]:
                    self.win.blit(gfx['quit'].subsurface(0, 120, 192, 60), (bx, 480))
                else:
                    self.win.blit(gfx['quit'].subsurface(0, 60, 192, 60), (bx, 480))
            else:
                self.win.blit(gfx['quit'].subsurface(0, 0, 192, 60), (bx, 480))

        # Refresh
        pg.display.flip()

    def load_resources(self):
        # Load graphics
        gfx_path = os.path.abspath('./res/gfx/')
        gfx_paths = {
            'bg_bricks': 'environment/bg_bricks.png',
            'bricks': 'environment/bricks.png',
            'lava': 'environment/lava.png',

            'checkbox': 'gui/checkbox.png',
            'menu_button': 'gui/menu.png',
            'welcome': 'gui/welcome.png',
            'hide': 'gui/hide.png',
            'resume': 'gui/resume.png',
            'reset': 'gui/reset.png',
            'quit': 'gui/quit.png',

            'lr_tutorial': ('text/left_right_tutorial.png', 2),
            'jump_tutorial': ('text/jump_tutorial.png', 2),
            'digits': 'text/digits.png',
            'paused': 'text/paused.png',
            'music': 'text/music.png',
            'sfx': 'text/sfx.png',

            'player': 'player.png',
            'logo': 'logo.png'
        }
        for key, value in gfx_paths.items():
            if len(value) == 2:
                self.gfx[key] = utils.load_img(os.path.join(gfx_path, value[0]), None, (value[1], value[1]))
            else:
                self.gfx[key] = utils.load_img(os.path.join(gfx_path, value))

        # Load sounds
        sfx_path = os.path.abspath('./res/sfx/')
        sfx_paths = {
            'music': 'music.wav',
            'jump': 'jump.wav'
        }
        for key, value in sfx_paths.items():
            self.sfx[key] = pg.mixer.Sound(os.path.join(sfx_path, value))
            self.sfx[key].set_volume(.5)
            

class Platform:
    def __init__(self, pos, size, type: int = 0):
        self.pos = pos
        self.size = size
        self.type = type

    def get_rect(self):
        return pg.Rect(self.pos, self.size)
    
class Particle:
    def __init__(self, pos: tuple[int], velocity, screen: int, duration: int, wh):
        self.pos = pos
        self.vel = velocity
        self.screen = screen
        self.dur = duration
        self.passed_time = 0
        self.tex_pos = (random.randint(0, 504), random.randint(0, 504))
        self.wh = wh # Window Height

    def update(self):
        self.passed_time += 1

        self.vel[0] *= 0.96
        self.vel[1] += 0.4

        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]

        if self.pos[1] > self.wh - 136:
            self.pos[1] = self.wh- 136

        


if __name__ == "__main__":
    game = Game((1280, 720))
    game.run()
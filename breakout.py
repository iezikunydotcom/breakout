"""Breakout - a rainbow brick-breaker in pygame.

Run with:   python breakout.py
Controls:   Mouse or arrow keys to move the paddle
            P to pause, R to restart, Esc to quit
"""

import colorsys
import random
import sys

import pygame

WIDTH, HEIGHT = 480, 640
FPS = 60

PADDLE_W, PADDLE_H = 90, 12
PADDLE_Y = HEIGHT - 30
BALL_R = 6
BALL_SPEED = 3.4

BRICK_ROWS, BRICK_COLS = 5, 8
BRICK_W, BRICK_H = 54, 20
BRICK_GAP = 4
BRICK_TOP = 60
BRICK_LEFT = 8

LIVES = 3

COLORS = {
    "bg": (15, 23, 42),
    "cell_a": (14, 23, 41),
    "cell_b": (11, 18, 32),
    "paddle": (148, 163, 184),
    "ball": (255, 255, 255),
    "text": (226, 232, 240),
    "muted": (148, 163, 184),
    "accent": (74, 222, 128),
}


def hsl_to_rgb(h, s=90, l=55):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l / 100.0, s / 100.0)
    return (round(r * 255), round(g * 255), round(b * 255))


class Breakout:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Breakout")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui", 24)
        self.font_big = pygame.font.SysFont("segoeui", 42, bold=True)
        self.font_small = pygame.font.SysFont("segoeui", 16)

        self.paddle_x = WIDTH // 2 - PADDLE_W // 2
        self.ball = None
        self.ball_dx = BALL_SPEED
        self.ball_dy = -BALL_SPEED
        self.bricks = []
        self.score = 0
        self.lives = LIVES
        self.state = "start"   # start | running | paused | over | won
        self.reset_round()
        self.draw()

    # -------- game state --------

    def reset_round(self):
        self.ball = [self.paddle_x + PADDLE_W // 2, PADDLE_Y - BALL_R]
        self.ball_dx = BALL_SPEED * random.choice((-1, 1))
        self.ball_dy = -BALL_SPEED

    def new_game(self):
        self.score = 0
        self.lives = LIVES
        self.bricks = []
        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                x = BRICK_LEFT + col * (BRICK_W + BRICK_GAP)
                y = BRICK_TOP + row * (BRICK_H + BRICK_GAP)
                hue = (row * BRICK_COLS + col) * 360 / (BRICK_ROWS * BRICK_COLS)
                self.bricks.append((pygame.Rect(x, y, BRICK_W, BRICK_H), hue))
        self.paddle_x = WIDTH // 2 - PADDLE_W // 2
        self.reset_round()

    def start(self):
        self.new_game()
        self.state = "running"

    def toggle_pause(self):
        if self.state == "running":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "running"

    # -------- update --------

    def update(self):
        self.ball[0] += self.ball_dx
        self.ball[1] += self.ball_dy

        # walls and ceiling
        if self.ball[0] - BALL_R <= 0 or self.ball[0] + BALL_R >= WIDTH:
            self.ball_dx = -self.ball_dx
        if self.ball[1] - BALL_R <= 0:
            self.ball_dy = -self.ball_dy

        # paddle
        paddle = pygame.Rect(self.paddle_x, PADDLE_Y, PADDLE_W, PADDLE_H)
        if self.ball_dy > 0 and paddle.collidepoint(self.ball[0], self.ball[1] + BALL_R):
            offset = (self.ball[0] - paddle.centerx) / (PADDLE_W / 2)
            self.ball_dx = offset * BALL_SPEED * 1.4
            self.ball_dy = -abs(self.ball_dy)

        # bricks
        ball_rect = pygame.Rect(self.ball[0] - BALL_R, self.ball[1] - BALL_R, BALL_R * 2, BALL_R * 2)
        for brick, hue in list(self.bricks):
            if brick.colliderect(ball_rect):
                self.bricks.remove((brick, hue))
                self.ball_dy = -self.ball_dy
                self.score += 10
                break

        # lost ball
        if self.ball[1] - BALL_R > HEIGHT:
            self.lives -= 1
            if self.lives <= 0:
                self.state = "over"
            else:
                self.reset_round()

        # win
        if not self.bricks:
            self.state = "won"

    # -------- input --------

    def handle_key(self, key):
        if key == pygame.K_p:
            self.toggle_pause()
        elif key == pygame.K_r:
            self.start()
        elif key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        elif key in (pygame.K_LEFT, pygame.K_a):
            if self.state in ("start", "over", "won"):
                self.start()
            self.paddle_x = max(0, self.paddle_x - 14)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            if self.state in ("start", "over", "won"):
                self.start()
            self.paddle_x = min(WIDTH - PADDLE_W, self.paddle_x + 14)

    # -------- drawing --------

    def draw(self):
        self.screen.fill(COLORS["cell_b"])
        for y in range(0, HEIGHT, 16):
            for x in range(0, WIDTH, 16):
                if (x // 16 + y // 16) % 2 == 0:
                    pygame.draw.rect(self.screen, COLORS["cell_a"], (x, y, 16, 16))

        # bricks
        for brick, hue in self.bricks:
            pygame.draw.rect(self.screen, hsl_to_rgb(hue), brick, border_radius=6)

        # paddle and ball
        pygame.draw.rect(self.screen, COLORS["paddle"], (self.paddle_x, PADDLE_Y, PADDLE_W, PADDLE_H), border_radius=6)
        if self.ball:
            pygame.draw.circle(self.screen, COLORS["ball"], (round(self.ball[0]), round(self.ball[1])), BALL_R)

        # HUD
        score_txt = self.font.render(f"Score: {self.score}", True, COLORS["text"])
        lives_txt = self.font.render("Lives: " + "♥" * self.lives, True, COLORS["muted"])
        self.screen.blit(score_txt, (16, 12))
        self.screen.blit(lives_txt, (WIDTH - lives_txt.get_width() - 16, 12))

        if self.state == "start":
            self.draw_overlay("Breakout", "Break all the rainbow bricks.\nMouse or arrows to move - P to pause", "Press an arrow key or R to start")
        elif self.state == "paused":
            self.draw_overlay("Paused", "", "Press P to resume")
        elif self.state == "over":
            self.draw_overlay("Game Over", f"Final score: {self.score}", "Press R to play again")
        elif self.state == "won":
            self.draw_overlay("You win!", f"Final score: {self.score}", "Press R to play again")

        pygame.display.flip()

    def draw_overlay(self, title, message, action):
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((11, 18, 32, 205))
        self.screen.blit(dim, (0, 0))
        t = self.font_big.render(title, True, COLORS["text"])
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 90))
        for i, line in enumerate(message.split("\n")):
            m = self.font_small.render(line, True, COLORS["muted"])
            self.screen.blit(m, (WIDTH // 2 - m.get_width() // 2, HEIGHT // 2 - 35 + i * 24))
        a = self.font.render(action, True, COLORS["accent"])
        self.screen.blit(a, (WIDTH // 2 - a.get_width() // 2, HEIGHT // 2 + 50))


def main():
    game = Breakout()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                game.handle_key(event.key)
            if event.type == pygame.MOUSEMOTION and game.state in ("running", "paused"):
                game.paddle_x = max(0, min(WIDTH - PADDLE_W, event.pos[0] - PADDLE_W // 2))

        if game.state == "running":
            game.update()
        game.draw()
        game.clock.tick(FPS)


if __name__ == "__main__":
    main()

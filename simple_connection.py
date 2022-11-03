from pynet import net, NetView
from pygame import Vector2
import pygame
import random

pygame.font.init()
FONT = pygame.font.Font(None, 20)

def get_random_color():
    return (
        random.randrange(0, 255),
        random.randrange(0, 255),
        random.randrange(0, 255)
    )

@net.instanceable
class Player(NetView):
    def __init__(self):
        super(Player, self).__init__()
        self.position = Vector2(50, 50)
        self.speed = 100
        self.nickname = ""
        self.nickname_image = None

    def net_init(self, nickname):
        self.nickname = nickname
        self.nickname_image = FONT.render(self.nickname, 16, (255, 255, 255))

        if self.net_view.is_mine():
            self.color = (255, 255, 255)
        else:
            self.color = (255, 0, 0)

    def net_update(self):
        self.call_rpc(
            "update_player",
            (self.position.x, self.position.y),
            target=net.OTHERS
        )

    @net.rpc
    def update_player(self, position):
        self.position = Vector2(position)

    @net.rpc
    def change_color(self, color):
        self.color = color

    @net.rpc
    def move(self, x, y):
        self.position = Vector2(x, y)

    def update(self, dt):
        if not self.net_view.is_mine():
            return

        keys = pygame.key.get_pressed()

        if keys[pygame.K_t]:
            self.color = get_random_color()
            self.call_rpc("change_color", self.color)

        direction = Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w]
        )

        if direction.magnitude_squared():
            self.position += direction.normalize() * self.speed * dt

    def draw(self, sf):
        pygame.draw.circle(sf, self.color, self.position, 10)

        pos = Vector2(self.position.x, self.position.y - 15) - Vector2(self.nickname_image.get_width() / 2, self.nickname_image.get_height())

        sf.blit(self.nickname_image, pos)

def on_connect():
    print("Connected with id =", net.client_id)
    net.instantiate(Player, random.choice([
        "Hernesto",
        "Peter",
        "Jose",
        "Tulipan",
        "Romuald",
    ]))

def main():
    sc = pygame.display.set_mode((800, 600))

    net.init(
        on_connect=on_connect
    )
    
    net.connect(("localhost", 987))

    clock = pygame.time.Clock()
    run = True
    while run:
        dt = clock.tick(60) / 1000
        net.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        sc.fill(0x0)

        for obj in net.objects:
            obj.update(dt)

        for obj in net.objects:
            obj.draw(sc)

        pygame.display.update()

    net.stop()

main()
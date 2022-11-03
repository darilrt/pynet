from pynet import net, NetView
from pygame import Vector2
import pygame
import random

ball_ref = None
paddel_ref = None

@net.instanceable
class Ball(NetView):
    def __init__(self):
        super(Ball, self).__init__()
        self.position = Vector2(400, 300)
        self.direction = Vector2(1, 1).normalize()
        self.speed = 200
        self.radius = 10
        
        self.rect = pygame.Rect((0, 0), (self.radius * 2, self.radius * 2))
        self.rect.center = self.position
        
    def net_init(self, direction):
        global ball_ref
        
        self.direction = Vector2(direction).normalize()
        
        if net.is_master():
            ball_ref = self
    
    def net_update(self):
        self.call_rpc(
            "update_state", 
            tuple(self.position),
            tuple(self.direction),
            self.speed,
            target=net.OTHERS
        )
        
    @net.rpc
    def update_state(self, position, direction, speed):
        self.position = Vector2(position)
        self.direction = Vector2(direction)
        self.speed = speed
    
    def update(self, dt):
        self.position += self.direction * dt * self.speed
        
        paddles = net.get_objects_by_class(Paddle)
        
        if self.position.x < -10:
            self.position.x = 400
            self.speed = 200
            self.direction = Vector2(1, random.choice([-1, 1])).normalize()
            
            for paddle in paddles:
                if paddle.side == "right":
                    paddle.points += 1
        
        if self.position.x > 810:
            self.position.x = 400
            self.speed = 200
            self.direction = Vector2(-1, random.choice([-1, 1])).normalize()
            
            for paddle in paddles:
                if paddle.side == "left":
                    paddle.points += 1
            
        
        if self.position.y < 10:
            self.position.y = 10
            self.direction.y = -self.direction.y
        
        if self.position.y > 590:
            self.position.y = 590
            self.direction.y = -self.direction.y
        
        self.rect.center = self.position
        for paddle in paddles:
            if paddle.rect.colliderect(self.rect):
                self.direction.x = -self.direction.x
                self.speed *= 1.25
    
    def draw(self, sf):
        pygame.draw.circle(sf, (255, 255, 255), self.position, 10)

@net.instanceable
class Paddle(NetView):
    def __init__(self):
        super(Paddle, self).__init__()
        self.position = Vector2(20, 10)
        self.size = 50
        self.speed = 500
        self.rect = pygame.Rect(self.position, (20, self.size))
        self.points = 0
    
    def net_init(self, side):
        global paddel_ref
        
        if self.net_view.is_mine():
            paddel_ref = self
        
        self.side = side
        
        if self.side == "left":
            self.position = Vector2(20, 10)
            
        elif self.side == "right":
            self.position = Vector2(760, 10)
        
        self.rect = pygame.Rect(self.position, (20, self.size))
     
    def net_update(self):
        self.call_rpc(
            "update_state", 
            tuple(self.position),
            target=net.OTHERS
        )
        
    @net.rpc
    def update_state(self, position):
        self.position = Vector2(position)
     
    def update(self, dt):
        if not self.net_view.is_mine():
            return
        
        keys = pygame.key.get_pressed()
        
        self.position.y += (keys[pygame.K_s] - keys[pygame.K_w]) * self.speed * dt
        
    def draw(self, sf):
        self.rect.topleft = self.position
        pygame.draw.rect(sf, (255, 255, 255), self.rect)

def on_reconnect():
    on_connect()

def on_disconnect():
    net.connect()
    
def on_connect():
    if net.is_master():
        net.instantiate(
            Ball,
            [random.choice([-1, 1]), random.choice([-1, 1])]
        )
        net.instantiate(
            Paddle,
            "left"
        )
    else:
        net.instantiate(
            Paddle,
            "right"
        )
    
def main():
    global ball_ref
    
    net.init(
        on_connect=on_connect,
        on_reconnect=on_reconnect,
        on_disconnect=on_disconnect
    )
    
    sc = pygame.display.set_mode((800, 600))

    pygame.font.init()
    font = pygame.font.Font(None, 20)
    left_points = 0
    right_points = 0
    
    net.connect(("localhost", 987))
    
    clock = pygame.time.Clock()
    run = True
    while run:
        dt = clock.tick(60) / 1000
        net.update()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
        
        sc.fill(0)
        
        if net.is_connected and net.is_master() and len(net.get_objects_by_class(Paddle)) < 2:
            if ball_ref == None:
                net.instantiate(
                    Ball, 
                    [random.choice([-1, 1]), random.choice([-1, 1])]
                )
                paddel_ref.net_init("left")
                paddel_ref.points = 0
                right_points = 0
                pass
                
            else:
                ball_ref.position = Vector2(400, 300)
        
        for o in net.objects:
            o.update(dt)
            o.draw(sc)
            
            if isinstance(o, Paddle):
                if o.side == "left":
                    left_points = o.points
                    
                elif o.side == "right":
                    right_points = o.points
        
        sc.blit(font.render(str(left_points), 16, (255, 255, 255)), (100, 20))
        sc.blit(font.render(str(right_points), 16, (255, 255, 255)), (700, 20))
        
        print(net.is_connected)
        
        pygame.display.update()
    
    net.stop()

if __name__ == "__main__":
    main()
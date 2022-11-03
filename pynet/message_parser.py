import socket
import json

class MessageParser:
    def __init__(self):
        self.buffer = ""
        
    def add(self, data):
        self.buffer += data
    
    def get_next(self):
        sub_buffer = ""
        
        i = 0
        capture = False
        for c in self.buffer:
            if c == "<":
                capture = True
            
            elif capture:
                if c == ">":
                    capture = False
                    self.buffer = self.buffer[i + 1:]
                    return json.loads(sub_buffer)
                
                else:
                    sub_buffer += c
            
            i += 1
        
        return None
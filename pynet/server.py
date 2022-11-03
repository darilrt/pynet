from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread, Event

from .message_parser import MessageParser
from .models import *

import socket as sock
import uuid
import json

class ClientObject:
    def __init__(self, object_id, id, init_data):
        self.object_id = object_id
        self.uuid = id
        self.init_data = init_data

class Client:
    last_id = 0
    server = None
    
    def __init__(self, address):
        Client.last_id += 1
        self.id = Client.last_id
        self.address = address
        self.message_parser = MessageParser()
        self.objects = []
        self.is_alive = True
        
        self.routes = {
            "call_rpc": self.call_rpc,
            "instatiate_object": self.instatiate_object,
            "connect": self.connect,
            "get_all_objects": self.get_all_objects,
            "destroy_object": self.destroy_object,
            "yessir": self.yessir
        }
    
    def check_messages(self):
        message = self.message_parser.get_next()
        
        while message != None: 
            if message["data"]["_client_id"] != -1 and message["data"]["_client_id"] != self.id:
                self.send(MessageModel("you_are_disconnected", {}))
            
            elif message["type"] in self.routes.keys():
                self.routes[message["type"]](message["data"])
            
            message = self.message_parser.get_next()

    def get_object_by_uuid(self, uuid):
        for obj in self.objects:
            if obj.uuid == uuid:
                return obj
        
        return None
    
    def call_rpc(self, data):
        Client.server.brodcast(
            MessageModel("call_rpc", data | {"client_id": self.id}),
            senderId = self.id if data["target"] == 2 else None
        )
    
    def connect(self, data):
        if Client.server.master == None:
            Client.server.set_master(self)
        
        self.send(MessageModel(
            "connected", 
            {
                "client_id": self.id,
                "master_id": Client.server.master.id
            }
        ))
    
    def destroy_object(self, data):
        instance = self.get_object_by_uuid(data["uuid"])
        
        if instance != None:
            Client.objects.remove(instance)
            Client.server.brodcast(MessageModel("destroy_object", data | {"client_id": self.id}))
    
    def get_all_objects(self, data):
        for client in Client.server.clients:
            for obj in client.objects:
                self.send(MessageModel(
                    "instatiate_object", 
                    {
                        "client_id": client.id, 
                        "object_id": obj.object_id,
                        "uuid": obj.uuid,
                        "args": obj.init_data
                    }
                ))
    
    def instatiate_object(self, data):
        obj = ClientObject(data["object_id"], str(uuid.uuid4()), data["args"])
        self.objects.append(obj)
        
        Client.server.brodcast(MessageModel(
            "instatiate_object",
            {
                "client_id": self.id, 
                "object_id": obj.object_id,
                "uuid": obj.uuid,
                "args": data["args"]
            }
        ))
    
    def yessir(self, data):
        self.is_alive = True
    
    def send(self, model):
        package = "<" + json.dumps(model.to_dict()) + ">"
        Client.server.socket.sendto(package.encode(), self.address)

class Server:
    master = None

    def __init__(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.address = ("", 0)
        self.threads = []
        self.is_running = False
        self.force_purge = False
        
        self.clients = []
        
        self.exit_flag = Event()
    
    def connect(self):
        self.socket.bind(self.address)
        self.socket.settimeout(1.0)
        
    def recv_data(self):
        while self.is_running:
            try:
                data, addr = self.socket.recvfrom(2048)
            
                client = self.get_client(addr)
                client.message_parser.add(data.decode())
                client.check_messages()
            
            except sock.timeout:
                pass
                
            except sock.error as e:
                #self.force_purge = True
                pass
            
            except Exception as e:
                print(f"\n{e}", end="\n:>")
        
    def get_client(self, addr):
        for client in self.clients:
            if client.address == addr:
                return client
        
        cli = Client(addr)
        self.clients.append(cli)
        return cli
    
    def brodcast(self, model, senderId=None):
        for client in self.clients:
            if senderId == None or client.id != senderId:
                client.send(model)
    
    def start_threads(self):
        self.add_and_start_thread(Thread(target=self.recv_data))
        self.add_and_start_thread(Thread(target=self.client_purge))
    
    def add_and_start_thread(self, thread):
        self.threads.append(thread)
        thread.start()
        
    def client_purge(self):
        while not self.exit_flag.wait(timeout=2.500) or self.force_purge:
            self.force_purge = False
            
            to_remove = []
            
            for client in self.clients:
                if not client.is_alive:
                    to_remove.append(client)
                    continue
                
                client.is_alive = False
                client.send(MessageModel("are_you_alive", {}))
            
            for client in to_remove:
                self.clients.remove(client)
            
            for client in to_remove:
                self.brodcast(MessageModel("client_disconnected",  {"client_id": client.id}))
                
            if Server.master not in self.clients:
                if len(self.clients) > 0:
                    self.set_master(self.clients[0])
                
                else:
                    Server.master = None
    
    def set_master(self, client):
        Server.master = client
        
        self.brodcast(MessageModel("set_master", {"master_id": client.id}))
    
    def serve(self, address, interactive=True):
        self.address = address
        
        self.connect()
        self.is_running = True
        Client.server = self
    
        self.start_threads()
        
        while self.is_running and interactive:
            data = input(":>")
            
            if data == "exit":
                self.is_running = False
            
            elif data == "list":
                if Server.master:
                    print(f"master = {Server.master.id}")
                
                for client in self.clients:
                    print(f"Client id={client.id} addr={client.address}")
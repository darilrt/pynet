from socket import socket, AF_INET, SOCK_DGRAM
from threading import Thread, Event

from .message_parser import MessageParser
from .models import *

import socket as sock
import json
import time

class BaseNetObject:
    def __init__(self):
        pass

class NetViewInfo:
    def __init__(self, uuid, owner_id):
        self.uuid = uuid
        self.owner_id = owner_id
        
    def is_mine(self):
        return net.client_id == self.owner_id

    def __str__(self):
        return f"NetViewInfo(uuid={self.uuid}, is_mine={self.is_mine()})"
    
class NetView:
    def __init__(self):
        self.net_view = net._object_meta
        
        net._object_meta = None
        
    def net_init(self):
        pass
        
    def net_update(self):
        pass
        
    def call_rpc(self, method_name, *args, **kwargs):
        rpc_name = f"{self.__class__.__name__}.{method_name}"
        net.call_rpc(rpc_name, self.net_view.uuid, *args, **kwargs)
 
class net:
    ALL = 1
    OTHERS = 2
    
    address = ("", 80)
    objects = []
    client_id = -1
    master_id = None
    is_connected = False
    on_connect = None
    on_disconnect = None
    on_reconnect = None
    
    # private
    _socket = socket(AF_INET, SOCK_DGRAM)
    _rpcs = {}
    _threads = []
    _is_running = False
    _message_parser = MessageParser()
    _instanceables = []
    _object_meta = {}
    _event_tick = Event()
    _last_tick = 0
    _token = ""
    _reconnect = False
    
    @staticmethod
    def is_master():
        return net.master_id == net.client_id
    
    @staticmethod
    def instanceable(p_class):
        net._instanceables.append(p_class)
        return p_class
    
    @staticmethod
    def instantiate(p_class, *args):
        if not net.is_connected:
            print("Network is not connected")
            return
        
        net.send(MessageModel("instatiate_object", {
            "object_id": net._instanceables.index(p_class),
            "args": args
        }))
    
    @staticmethod
    def destroy(instance):
        if not net.is_connected:
            print("Network is not connected")
            return
        
        if not instance.net_view.is_mine():
            return
        
        uuid = instance.net_view.uuid
        net.objects.remove(instance)
        
        net.send(MessageModel("destroy_object", {"uuid": uuid}))
    
    @staticmethod
    def init(on_connect=None, on_reconnect=None, on_disconnect=None):
        net.on_connect = on_connect
        net.on_reconnect = on_reconnect
        net.on_disconnect = on_disconnect
        
        net._socket.settimeout(1.0)
        
        net._is_running = True
        th = Thread(target=net._listen_socket)
        net._threads.append(th)
        th.start()
        
    @staticmethod
    def connect(address=None, callback=None):
        if address: net.address = address
        if callback: net.on_connect = callback
        
        net.send(MessageModel("connect", {}))
        
    @staticmethod
    def get_objects_by_class(class_name):
        return [o for o in net.objects if isinstance(o, class_name)]
    
    @staticmethod
    def stop():
        net._is_running = False
        
    @staticmethod
    def _listen_socket():
        while net._is_running:
            try:
                data, addr = net._socket.recvfrom(2048)
                
                net._message_parser.add(data.decode())
                net.parse_messages()
            
            except sock.timeout:
                pass
            
            except sock.error as e:
                net.is_connected = False
                pass
    
    @staticmethod
    def update(tick=30):
        elapsed = time.time() - net._last_tick
        
        if elapsed >= (1 / tick):
            
            for obj in net.objects:
                if obj.net_view.is_mine():
                    obj.net_update()
            
            net._last_tick = time.time()
    
    @staticmethod
    def parse_messages():
        message = net._message_parser.get_next()

        while message != None:
            if message["type"] == "connected":
                net.client_id = message["data"]["client_id"]
                net.is_connected = True
               
                net.master_id = message["data"]["master_id"]
                
                net.objects = []
                
                if net._reconnect:
                    if net.on_reconnect != None: net.on_reconnect()
                else:
                    if net.on_connect != None: net.on_connect()
                
                net.send(MessageModel("get_all_objects", {}))
            
            if not net.is_connected:
                message = net._message_parser.get_next()
                continue
            
            if message["type"] == "call_rpc" and message["data"]["name"] in net._rpcs:
                net._rpcs[message["data"]["name"]](message["data"]["client_id"], *message["data"]["args"])
            
            elif message["type"] == "set_master":
                net.master_id = message["data"]["master_id"]
                
            elif message["type"] == "instatiate_object":
                data = message["data"]
                
                instance = net.get_object_by_uuid(data["uuid"])
                
                if instance == None:
                    p_class = net._instanceables[data["object_id"]]
                
                    net._object_meta = NetViewInfo(data["uuid"], data["client_id"])
                    
                    instance = p_class()
                    instance.net_init(*data["args"])
                    
                    net.objects.append(instance)
            
            elif message["type"] == "destroy_object":
                instance = net.get_object_by_uuid(message["data"]["uuid"])
                
                if instance != None:
                    net.objects.remove(instance)
            
            elif message["type"] == "you_are_disconnected":
                net.is_connected = False
                net.client_id = -1
                
                net._reconnect = True
                if net.on_disconnect != None: net.on_disconnect()
            
            elif message["type"] == "are_you_alive":
                net.send(MessageModel("yessir", {}))
            
            elif message["type"] == "client_disconnected":
                net.remove_object_by_owner(message["data"]["client_id"])
            
            message = net._message_parser.get_next()
        
    @staticmethod
    def rpc_ex(rpc_name):
        def register_rpc(func):
            net._rpcs[rpc_name] = func
        
        return register_rpc
    
    @staticmethod
    def get_object_by_uuid(uuid):
        for obj in net.objects:
            if obj.net_view.uuid == uuid:
                return obj
                
        return None
    
    @staticmethod
    def remove_object_by_owner(owner_id):
        net.objects = [o for o in net.objects if o.net_view.owner_id != owner_id]
    
    @staticmethod
    def rpc(method):
        def rpc_callback_ex(client_id, uuid, *args):
            obj = net.get_object_by_uuid(uuid)
            method(obj, *args)
        
        net._rpcs[method.__qualname__] = rpc_callback_ex
    
    @staticmethod
    def call_rpc(rpc_name, *args, **kwargs):
        net.send(MessageModel("call_rpc", {
            "name": rpc_name,
            "target": kwargs["target"] if "target" in kwargs else net.ALL,
            "args": list(map(lambda x: net.try_to_dict(x), args))
        }))
    
    @staticmethod
    def send(model):
        model.data["_client_id"] = net.client_id
        package = "<" + json.dumps(model.to_dict()) + ">"
        net._socket.sendto(package.encode(), net.address)
    
    @staticmethod
    def try_to_dict(x):
            try:
                return x.to_dict()
            
            except:
                return x
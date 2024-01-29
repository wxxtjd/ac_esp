import utils
import ctypes
from ctypes import wintypes
import struct
import time
import numpy as np

PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
VIEW_MAXTRIX_ADDR= 0x00400000 + 0x17DFFC-0x06C+0x4*16

kernel32 = ctypes.windll.kernel32

process_info = utils.GetInfoByName("ac_client.exe")
process_pid = int(process_info['pid'])
handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, process_pid)
if not handle: print("Failed to open process. Error code:", kernel32.GetLastError()) #If failed to get handle.

base_address = utils.GetBaseAddress(handle)

#Base Address of my player
MyPlayerBaseOffset = 0x0017E0A8
MyPlayerBase = base_address + MyPlayerBaseOffset
MyPlayerInfoOffsets = {"X":0x0028, "Y_head":0x000C, "Y_foot":0x0030, "Z":0x002C, "View_Hor":0x0034, "View_Ver":0x0038, "Ammo":0x0140}

#Base Address of EntityList
EntityListBaseOffset = 0x00191FCC
EntityListBase = base_address + EntityListBaseOffset
EntityOffsetGap = 0x0004
EntityNumBase = base_address + 0x0018AC0C
EntityInfoOffests = {"X":0x0004, "Z":0x0008, "Y_head":0x000C, "Y_foot":0x0030, "Name":0x0205, "HP":0x00EC}

class DataManager():
    def __init__(self):
        self.TypeDict = {"X":[ctypes.create_string_buffer, 4, "f"],
                         "Y":[ctypes.create_string_buffer, 4, "f"],
                         "Z":[ctypes.create_string_buffer, 4, "f"],
                         "Y_head":[ctypes.create_string_buffer, 4, "f"],
                         "Y_foot":[ctypes.create_string_buffer, 4, "f"],
                         "View_Hor":[ctypes.create_string_buffer, 4, "f"],
                         "View_Ver":[ctypes.create_string_buffer, 4, "f"],
                         "Ammo":[ctypes.c_int, None, int],
                         "HP":[ctypes.create_string_buffer, 4, "<I"],
                         "Name":[ctypes.create_string_buffer, 32, str],
                         "Matrix":[ctypes.create_string_buffer, 4, "f"],
                         "int":[ctypes.create_string_buffer, 4, "<I"]}
    
    def GetDataType(self, data_name):
        return self.TypeDict[data_name]
    
    def decode_data(self, data, decode_key):
        decoded_data = None
        #In case of string
        if decode_key == str:
            NULL_INDEX = data.raw.find(b'\x00')
            decoded_data = data.raw[:NULL_INDEX].decode()

        #In case of int
        elif decode_key == int:
            decoded_data = int.from_bytes(data.raw, 'little')

        #Else cases
        else:
            decoded_data = struct.unpack(decode_key, data.raw)[0]

        return decoded_data

def ReadMem(address, key):
    buffer = None
    datm = DataManager()
    data_type, BUFFERSIZE, decode_key = datm.GetDataType(key)

    #Make a buffer for data
    if BUFFERSIZE:
        buffer = data_type(BUFFERSIZE)
    else:
        buffer = data_type()

    success = kernel32.ReadProcessMemory(handle, address, buffer, BUFFERSIZE, None)

    if success:
        data = datm.decode_data(buffer, decode_key)
        return data
    else:
        return 0

def UnlimitedAmmo():
    ammo_amount = ctypes.c_int(20)

    #Get address of ammo memory.
    address = utils.FollowPointerChain([MyPlayerInfoOffsets['Ammo']], MyPlayerBase, handle)
    success = kernel32.WriteProcessMemory(handle, address, ctypes.byref(ammo_amount), ctypes.sizeof(ammo_amount), None)
    print(success, kernel32.GetLastError())

def GetMyInfo():
    BUFFER_SIZE = 4
    
    MyInfoDict = {}
    MyAddresses = {}

    for key in list(MyPlayerInfoOffsets.keys())[:-1]:
        #Get the address of an information.
        address = utils.FollowPointerChain([MyPlayerInfoOffsets[key]], MyPlayerBase, handle)
        MyAddresses[key] = address

    for key in list(MyPlayerInfoOffsets.keys())[:-1]:
        #Get the address of an information.
        address = MyAddresses[key]

        #Make a buffer for saving an information.
        info = ctypes.create_string_buffer(BUFFER_SIZE)

        #Read a data from memory of process.
        success = kernel32.ReadProcessMemory(handle, address, info, BUFFER_SIZE, None)

        if success:
            val = struct.unpack("f", info.raw)[0]
            MyInfoDict[key] = val
        else:
            print("Read failed. Error code:", kernel32.GetLastError())

    return MyInfoDict

def GetViewMatrix():
    view_matrix = np.array([])
    for idx in range(16):
        element = ReadMem(VIEW_MAXTRIX_ADDR + (4*idx), "Matrix")
        view_matrix = np.append(view_matrix, element)
    
    view_matrix = view_matrix.reshape(4,4)
    
    return view_matrix

def GetEntityList():
    EntityAddresses = []
    EntityNum = ReadMem(EntityNumBase, "int")

    for EntityIDX in range(EntityNum-1):
        EntityAddress = utils.FollowPointerChain([EntityOffsetGap*EntityIDX], EntityListBase, handle)
        EntityAddresses.append(EntityAddress)
    
    #Buffer for entity
    EntityList = []

    #State var for checking found all entity .
    state = 1

    for EntityAddress in EntityAddresses:
        #Entity information dict
        Entity = {}

        #Get entity information
        for key, offset in list(EntityInfoOffests.items()):
            address = utils.FollowPointerChain([offset], EntityAddress, handle)

            try:
                data = ReadMem(address, key)
                Entity[key] = data
            except:
                state = 0
                break
       
        #If find all entity -> break
        if state:
            if len(Entity) != 0:
                if Entity["HP"] > 100:
                    Entity["HP"] = 0
                EntityList.append(Entity)
        else:
            break
    
    return EntityList

def World2Screen(entities, view_matrix, width=2560, height=1600):
    entity_info_dict = {}
    for entity in entities:
        entity_x = entity["X"]
        entity_z = entity["Z"]
        entity_y = entity["Y_head"]
        entity_w = 1

        enemy_matrix = np.array([entity_x, entity_z, entity_y, entity_w]).reshape(-1,1)

        screen_view = np.sum(view_matrix * enemy_matrix, axis=0)

        w_value = screen_view[3]
        x_value = screen_view[0]
        y_value = screen_view[1]

        camera_x = width / 2
        camera_y = height / 2

        x = camera_x + (camera_x*x_value / w_value)
        y = camera_y - (camera_y*y_value / w_value)
        if w_value > 0.001:
            entity_info_dict[entity["Name"]] = [x, y]
        else:
            entity_info_dict[entity["Name"]] = [0, 0]
    
    return entity_info_dict
        
def CalcDistance(myplayer, entities):

    entity_distance_dict = {}

    for entity in entities:
        my_x, my_y, my_z = myplayer["X"], myplayer["Y_foot"], myplayer["Z"]
        entity_x, entity_y, entity_z = entity["X"], entity["Y_head"], entity["Z"]

        distance_xz = ((entity_x - my_x)**2 + (entity_z - my_z)**2)**0.5
        distance = (distance_xz**2 + (entity_y - my_y)**2)**0.5
    
        entity_distance_dict[entity["Name"]] = distance

    return entity_distance_dict
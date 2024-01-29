import os
import pymem
import ctypes
import win32process

kernel32 = ctypes.windll.kernel32

INFO_NAMES = ['process_name', 'pid', 'session name', 'session number', 'memory use']

def GetInfoByName(name:str):
    try:
        #Get informations of process.
        out = os.popen(f'tasklist | findstr "{name}"').read()[:-1]
        out = " ".join(out.split())
        info_list = out.split()[:-1]
    except Exception as e:
        print(f"[ERROR] {e}")
        
    #Make a dict for information.
    info_dict = {}
    for idx in range(len(INFO_NAMES)):
        key = INFO_NAMES[idx]
        value = info_list[idx]
        info_dict[key] = value
    
    return info_dict

def GetBaseAddress(handle):
    process_modules = win32process.EnumProcessModules(handle)[0]
    return process_modules

def FollowPointerChain(offsets, address, handle):
    for offset in offsets:
        address_buffer = ctypes.c_int()

        success = kernel32.ReadProcessMemory(handle, address, ctypes.byref(address_buffer), 4, None)

        #Check request performed successfully.
        if success:
            address = address_buffer.value + offset
        else:
            error_code = kernel32.GetLastError()
            print(f"[Error] Failed to follow the pointer chain. {error_code}")
    
    return address


"""Module containing methods to access and manipulate the OS filesystem

Usage:
Import this module and call the methods to use them

All commands involving changing directory, getting directory contents and getting file contents should be passed to executeCommands. Check it's docstring for usage"""

import os
import sys
import string
import re

INVALID_COMMAND = 'invalid'
REVERT_PWD = 'revert'
STAY = 'as you were'

DISPLAY_CONTENTS_CMD = '.'
GO_UP_CMD = '..'
UNIX_SLASH = '/'

pwd = ''

def makeFilestorePath (name):
    """Returns the path of a directory or file from the filespace root

    For internal use only
    """

    global pwd

    return getPwd() + UNIX_SLASH + name
    
    
def makePath (name):
    """
    Returns a full path for the given file/directory

    Generally for internal use
    """
    global pwd

    return pwd + UNIX_SLASH + name
    
def makePwd(new_dir):
    """
    Returns a full path for the new pwd

    Generally for internal use
    """

    global pwd

    return makeInsideDir(pwd, new_dir)
    

def makeInsideDir(path, new_dir):
    """Returns a full path for a file/directory inside the given directory"""

    #if the pwd is root, the slash between new directories is not needed
    if path[:len(path)]== UNIX_SLASH:
        return path + new_dir
    else:
        return path + UNIX_SLASH + new_dir

def isInFilespace(path):
    """Returns whether or not a file is in the filespace

    Generally for internal use"""

    path = replaceBackSlashes(path)

    #if the path starts with the root dir
    if string.find(path, replaceBackSlashes(root)) is 0:
        return True
    else:
        return False


class NavigationException (Exception):
    def __init__ (self, value):
        self.value = value

    def __str__ (self):
        return self.value

def goUp():
    """Changes the pwd to the parent of the pwd

    Throws NavigationException if already at the root directory.

    For internal use only; to go up a directory, pass '..' to changePwd()"""
    
    global pwd

    #don't allow going back further than root
    if pwd == root:
        raise NavigationException("Can't go back further than root directory")

    #go up a directory level
    else:
        
        to_strip = ''

        #gets a list of all printable characters that aren't slashes
        for x in string.printable:
            if x != '/' and x != '\\':
                to_strip += x
                
        #strips the tailing directory name from the pwd
        pwd = string.rstrip(pwd, to_strip)

        #strips the tailing slash from the pwd unless the pwd is now the root
        if pwd [:len(pwd)] != UNIX_SLASH:
            pwd = pwd [:len(pwd)-1] 


def createFile (filename, path=None):
    """Returns file created at in the pwd with the specified filename"""
    global pwd

    if path == None:
        path = pwd
    else:
        createDir(path)

    filename = replaceBackSlashes(filename)

    full_filename = makeInsideDir(path, filename)

    if isInFilespace(full_filename):
        if not os.path.exists(full_filename):
            return open(full_filename, 'wb')
        else:
            raise OSError('File already exists')
    else:
        raise OSError('Path not in filespace')
      
def createDir(name):
    """Creates a with the specified name in the pwd

    Raises OSError if directory already exists or if the path is not in the filespace"""

    full_path = makePwd(name)

    if not os.path.exists(full_path):
        if isInFilespace(full_path):
            os.makedirs(full_path)  
        else:
            raise OSError('Path not in filespace')
    else:
        raise OSError('Directory already exists')

def getFileStatus(filename):
    """Returns the status of a given file

    Data is held in a tuple in format (full path name, file size, last access time, last modification time)

    Throws OSError if file is not valid

    For internal use only; pass the filename to executeCommands"""
    
    filename = replaceBackSlashes(filename)

    full_path = makePwd(filename)
    
    return makeFilestorePath(filename), os.path.getsize(full_path), os.path.getatime(full_path), os.path.getmtime(full_path)

def getFile(filename):
    """Returns a file object holding the specified file information and its size

    Throws OSError on bad filename or file outside of the filespace"""

    filename = replaceBackSlashes(filename)
    full_path = makePwd(filename)

    if isInFilespace(full_path):
        return open(full_path, "rb"), os.path.getsize(full_path)
    else:
        raise OSError("Invalid file")

def getFileContents(filename):
    """Returns the contents of a file as one long string

    Throws IOError on bad filename
    Throws OSError if file must be text but isn't"""
    
    filename = replaceBackSlashes(filename)
    full_path = makePwd(filename)

   
    if isInFilespace(full_path):
        with open(full_path) as file:
            return file.read()
    else:
        raise OSError("File is not in filespace")

def setRoot(directory):
    """Sets the root location of the filestore

    Absolute paths only"""
    global root, pwd

    directory = replaceBackSlashes(directory)
    
    root = directory
    
    pwd = root

def executeCommands(command):
    """Gets a string of commands and executes them

    Commands can be:
    '.' - return contents of directory
    '..' - go up a directory
    <directory name> - change to directory (relative)
    <file name> - return status of file

    These can be joined to create complex commands such as:
    '../../dir' - change directory to 'dir' where dir is in the parent of the current parent dir
    'dir1/dir2/file' - return file status of named file
    """

    global pwd

    old_pwd = pwd

    command = replaceBackSlashes(command)

    commands = string.split(command, UNIX_SLASH)
    message = ''
    ret = None

    for x in range(len(commands)):
        if x == len(commands) - 1:
            is_last_command = True
        else:
            is_last_command = False

        ret, message = singleExecution(commands[x], is_last_command)

        if message == INVALID_COMMAND:
            raise CommandException ("Invalid command")

    if message == REVERT_PWD:
        pwd = old_pwd

    if ret != None:
        return ret

class CommandException (Exception):
    def __init__ (self, value):
        self.value = value

    def __str__ (self):
        return self.value

def singleExecution(command, is_last_command):
    """Carries out a single command

    For internal use only; use executeCommands instead"""

    global pwd

    if command == DISPLAY_CONTENTS_CMD and is_last_command:
        return getPwdContents(), REVERT_PWD

    elif os.path.isfile(makePath(command)) and is_last_command:
        return getFileStatus(command), REVERT_PWD

    elif command == GO_UP_CMD:
        goUp()
        return None, STAY

    elif os.path.isdir(makePath(command)):
        pwd = string.rstrip(makePwd(command), '/')
        return None, STAY
    
    
    return None, INVALID_COMMAND
        

def getPwdContents():
    """Returns the contents of the pwd

    The returned data is held in a tuple, formatted as (name of file/directory, size in bytes)

    Directories are said to have a size of -1

    Throws OSError if there are broken symbolic links"""
    global pwd

    return getDirContents(pwd)

def getDirContents(directory):
    """Returns the contents of the specified directory

    Takes absolute paths"""

    directory = replaceBackSlashes(directory)

    contents = os.listdir(directory)
    contents.sort()

    files = []

    return_data = ()

    for x in contents:
        #add a slash to the end of directories
        if os.path.isdir(makePath(x)):
            x += UNIX_SLASH
            return_data += [x, -1], #dirs always have a size of -1 to help handling on other modules
        elif os.path.exists(makePath(x)):
            files.append(x)
    
    for x in files:
         return_data += [x, os.path.getsize(makePath(x))],

    return return_data

def getFilteredPwdContents():
    """Returns the contents of the pwd without config files/directories (starting with '.'"""

    data = getPwdContents()

    new_data = filter(isNotConfig, data)

    return new_data

def isNotConfig(data):
    """Returns if the file/directory is a non-config file/dir

    Generally for internal use"""

    for filename in data:
        if filename[:1] == '.':
            return False
        else:
            return True

def getPwd():
    """Returns the pwd

    Prefered as opposed to simply accessing the pwd field directly"""

    path = replaceBackSlashes(pwd)[len(replaceBackSlashes(root)):]
    
    return 'filespace:/' + path

def unrestrictFilespace():
    """Unrestricts the filespace, i.e. sets the filespace root to the system root"""
    global root, pwd

    root = platform_root
    
    pwd = root
      

def replaceBackSlashes(s):
    """Replaces backslases in a string with slashes"""

    return string.replace(s, '\\', '/')

root = os.getcwd() #root directory
    
pwd = root #present working directory

platform_root = ''

if sys.platform == 'win32':
    platform_root = root[:3]
else:
    platform_root = '/'

pwd_contents = [] #will hold the contents of the pwd


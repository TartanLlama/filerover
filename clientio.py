"""
ClientIO module deals with connecting to a server as a client, sending commands
and returning responses.

Usage:
    - Connect to server using connect(address)
    - Disconnect using disconnect()
    - Transfer files using FileTransfer class
    - Make requests to server using other functions:
        listDir()
        chDir(path)
        makeDir(path)
        getDir(filename)
        getFileProperties(filename)
        getFileText(filename)
    - Do not use functions labelled as "For internal use"

Exceptions:
    IOError - Thrown by functions when there is a connection/network problem
    OSError - If the server cannot/will not return data, or a file operation
              has failed.
    ValueError - If bad data has been returned by the server (if the server is
                 functioning properly, this should not occur)
    AttributeError - If the socket = None, i.e. if it has not been created
                     using connect(), or has been disconnected with
                     disconnect()
                   - If a file opened in the wrong mode is given as a parameter
                     to a function.
"""
__author__ = "Sean O'Kelly <so227@st-andrews.ac.uk>"
__date__ = "2010-11-13  23:18"

import socket
import string
import threading
import Queue
import time





###############################################################################
# Globals and initialisation
###############################################################################

#Constants - same across client and server
PORT_NUM = 56740 #unique port number based on my unix user id
TRANSFER_PORT_NUM = 56744 #other group member's port number
BUFFER_SIZE = 8192 #8kB - enough for anything like directory listing etc.
TIMEOUT = 30 #30 seconds
DIVIDER = "|" #To divide sections of transmissions (e.g. cmd and params)
LISTDIR_CMD = "LS"
CHDIR_CMD = "CD"
GETDIR_CMD = "GETCWD"
GETINFO_CMD = "INFO"
MKDIR_CMD = "MKDIR"
DOWNLOAD_CMD = "DOWN"
UPLOAD_CMD = "UP"
GETTEXT_CMD = "GETTEXT"
CONTINUE_CMD = "CONTINUE"
CANCEL_CMD = "CANCEL"
DISCONNECT_CMD = "DISCONNECT"
FAILURE_MSG = "FAIL" #just kidding
SUCCESS_MSG = "WIN"

#Variables
address = ""
client_socket = None

###############################################################################
# End of globals/initialisation
###############################################################################





###############################################################################
# Connect/Disconnect functions
###############################################################################

#connect function: to connect client_socket to the server
def connect(input_address=socket.gethostname()):
    """
    Usage:
        Connects to a server at address, initialises the module so that other
        functions in the module may be used.
    
    Takes in:
        address - address of server to connect to, current computer by default.
    
    Exceptions:
        IOError - if connection fails.
    """
    try:
        global address
        address = input_address
        global client_socket
        if client_socket != None:
            #Socket already exists, disconnect it so new connection can be made
            disconnect()
        #next: create socket object
        #AF_INET and SOCK_STREAM - constants defining type of socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((address, PORT_NUM))
        #client_socket.settimeout(30) #30 seconds for timeout
    
    except socket.herror:
        #socket has failed to connect because of address lookup error
        client_socket = None
        raise IOError("Address lookup failed.")
    except socket.gaierror:
        #socket has failed to connect because of invalid address
        client_socket = None
        raise IOError("Invalid address.")
    except socket.error:
        #socket has failed to connect due to network issue/refused connection
        client_socket = None
        raise IOError("Connection failed.")
#end of connect function


#disconnect function: to disconnect the socket
def disconnect(notify_server=True):
    """
    Usage:
        Disconnects from the server. Use after program is finished using the
        server. Will attempt to notify server of disconnect.
    """
    global client_socket
    #only perform actions if the socket exists.
    if client_socket != None:
        if notify_server:
            try:
                # Send DISCONNECT_CMD to let server know of disconnect.
                # ensures server can quit gracefully.
                sendMsg(DISCONNECT_CMD)
            except (IOError, AttributeError):
                # if there's an error, we tried to notify server but failed,
                # server has to deal with it, so we'll ignore.
                pass
        try:
            client_socket.close()
        except AttributeError:
            pass
        #Remove reference to old socket object
        client_socket = None
#end of disconnect function

###############################################################################
# End of connect/disconnect functions
###############################################################################





###############################################################################
# Functions for sending commands to server
###############################################################################

#listDir function: to get a list of directories from the server and return it
def listDir():
    """
    Usage:
        Requests a list of files/directories from the server.
    
    Returns:
        List of tuples in the form (file_name, file_size), one tuple for each
        file or directory - file_size is -1 for directories.
    
    Exceptions:
        IOError - If network IO (request for or receipt of data) fails.
                - If this is raised, the socket is probably not connected.
        OSError - If the server fails to retrieve directory info
                - Possibly if the directory has been deleted or similar?
        ValueError - If it receives badly formatted data from the server.
                   - This should never happen if server is working properly.
        AttributeError - If the socket = None, i.e. if it has not been created
                         using connect(), or has been disconnected with
                         disconnect()
    """
    try:
        data = sendCmdReceiveReply(LISTDIR_CMD)
    except (IOError, AttributeError): raise

    # If the server sends a failure message - cannot retrieve data
    if checkForFailure(data): 
        message = "Server: Could not return directory data."
        if len(data) >= 2:
            message = "Server: " + data[1]
        raise OSError(message)

    #Re-format data back into original form
    #  sendCmdReceiveReply automatically splits data into list
    #  this is incompatible with this function which receives complex data.
    data_str = ""
    for element in data:
        data_str += element + DIVIDER
    #remove last and first dividers:
    data = data_str[1:len(data_str) - 1]
    
    try:
        if data == "":
            data_list = []
        else:
            #Remove any random whitespace
            data = data.strip()
            #Split into a list of "name|size" strings
            data_list = data.split("\n")
            #For each array index in the list
            for i in xrange(0, len(data_list)):
                #split into [name, size]
                elem_list = data_list[i].split(DIVIDER)
                #change to tuple
                data_list[i] = (elem_list[0], int(elem_list[1]))
    except (IndexError, ValueError):
        #Something went wrong in the analysis of data from server, so it's
        #probably badly formatted data from server.
        raise ValueError("Bad data from server.")
    
    return data_list
#end of listDir function


#chDir function: to change the current directory of the server's filestore
def chDir(path):
    """
    Usage:
        Used to request to change the current directory of the filestore on the
        server.

    Takes in:
        path - path to change to.
    
    Exceptions:
        IOError - If network IO (request for or receipt of data) fails.
                - If this is raised, the socket is probably not connected.
        OSError - If the server cannot/will not change directory (i.e. because
                  of restrictions.)
        AttributeError - If the socket = None, i.e. if it has not been created
                         using connect(), or has been disconnected with
                         disconnect()
    """
    try:
        # "CD|dir_name" - recognised by server
        command = CHDIR_CMD + DIVIDER + path 
        data = sendCmdReceiveReply(command)
    except (IOError, AttributeError): raise
    
    if checkForFailure(data): #Server couldn't/wouldn't change directory
        message = "Server: Could not change directory."
        if len(data) >= 2:
            message = "Server: " + data[1]
        raise OSError(message)
#end of chDir function


#makeDir function: to change the current directory of the server's filestore
def makeDir(path):
    """
    Usage:
        Used to request to create a new directory on the server.

    Takes in:
        path - directory to create.
    
    Exceptions:
        IOError - If network IO (request for or receipt of data) fails.
                - If this is raised, the socket is probably not connected.
        OSError - If the server cannot/will not create directory (i.e. because
                  of restrictions.)
        AttributeError - If the socket = None, i.e. if it has not been created
                         using connect(), or has been disconnected with
                         disconnect()
    """
    try:
        # "MKDIR|dir_name" - recognised by server
        command = MKDIR_CMD + DIVIDER + path 
        data = sendCmdReceiveReply(command)
    except (IOError, AttributeError): raise
    
    if checkForFailure(data): #Server couldn't/wouldn't make dir
        message = "Server: Could not create directory."
        if len(data) >= 2:
            message = "Server: " + data[1]
        raise OSError(message)
#end of makeDir function


#getDir function: to get the current path from the server
def getDir():
    """
    Usage:
        Request that the server send the path of the current directory.

    Returns:
        The path of the current directory of the filestore on the server.
    
    Exceptions:
        IOError - If network IO (request for or receipt of data) fails.
                - If this is raised, the socket is probably not connected.
        OSError - If the server fails to retrieve directory info
                - Possibly if the directory has been deleted or similar?
        AttributeError - If the socket = None, i.e. if it has not been created
                         using connect(), or has been disconnected with
                         disconnect()
    """
    try:
        #Request to be sent current location in server's filesystem
        data = sendCmdReceiveReply(GETDIR_CMD)
    except (IOError, AttributeError): raise
    
    if checkForFailure(data): #The server cannot retrieve the data
        message = "Server: Could not return directory path."
        if len(data) >= 2:
            message = "Server: " + data[1]
        raise OSError(message)
    
    return data[0]
#end of getDir function


#getFileProperties function: to get details on a specified file from the server
def getFileProperties(filename):
    """
    Usage:
        Requests that the server send details for a file.
    
    Takes in:
        filename - The file name of the file whose details are being requested.
    
    Returns:
        Tuple of (full_path_name, file_size (bytes), last_access_time,
                  last_modification_time)
    
    Exceptions:
        IOError - If network IO (request for or receipt of data) fails.
                - If this is raised, the socket is probably not connected.
        OSError - If the server has failed to get data on the file.
                - e.g. if the file does not exist.
        ValueError - If it receives badly formatted data from the server.
                   - This should never happen if server is working properly.
        AttributeError - If the socket = None, i.e. if it has not been created
                         using connect(), or has been disconnected with
                         disconnect()
    """
    try:
        #"INFO|filename"-recognised by server
        command = GETINFO_CMD + "|" + filename
        data = sendCmdReceiveReply(command)
    except (IOError, AttributeError): raise

    #Server couldn't/wouldn't get file data.
    if checkForFailure(data):
        message = "Server: Could not get file data."
        if len(data) >= 2:
            message = "Server: " + data[1]
        raise OSError(message)
    
    try:
        # data is in form "a|b|c|d" for transit
        data = (data[0], int(data[1]), data[2], data[3])
        return data
    except (IndexError, ValueError):
        #Server transferred badly formatted data.
        raise ValueError("Bad data from server.")
#end of getFileProperties function

###############################################################################
# End of server command functions
###############################################################################




###############################################################################
# Code for file transfer
###############################################################################

#FileTransfer class - allows concurrent, queued (one at a time) file transfer
class FileTransfer(threading.Thread):
    """
    Usage:
        Create an object of this class to execute a file transfer (upload
        or download).
        File transfers will be made to run concurrently, so will not block the
        rest of the program, but will be queued to run one at a time, so that
        we don't have multiple transfers on the same port at the same time.
        To get the transfer's status, use getStatus() to get a tuple of
        information.
        Do not call any other methods in this class directly, simply create the
        object. Calling any other method will mess up the program's operation.
        Note - if it fails during transfer (not during negotiation/
        initialisation), no exception will be raised, failure can be detected
        through getStatus()
        File being read from/written to will automatically be closed at the
        completion of the transfer - file should not be closed externally due
        to the concurrent nature of this class.
    """
    
    #Constructor
    def __init__(self, filename, file_object, file_size=-1, download=True):
        """
        Constructor

        Usage:
            For an upload:
                my_transfer = Transfer(filename_to_save_as,
                                       file_object_to_read_from,
                                       file_size=exact_size_in_bytes
                                       download=False)
            For a download:
                my_transfer = Transfer(filename_of_file_to_download,
                                       file_object_to_write_to)
        
        Takes in:
            filename - If this transfer is an upload, the filename is the name
                       to save the uploaded file to on the server.
                       If this is a download, it is the name of the file to
                       download from server.
            file_object - If this is an upload, the file_object is the file to
                          read data from, and upload. Must be in "rb" mode.
                          If this is a download, the file_object is the file to
                          write downloaded data to. Must be in "wb" mode.
            file_size - If this is an upload, this is required, and must be the
                        exact size of the file in bytes.
                        If this is a download, this is not required and will be
                        ignored.
            download - Boolean for whether this is a download or an upload.
                       should be True (default) if this is a download,
                       False for an upload.

        Exceptions:
            AttributeError - If the file is open in the wrong mode.
                           - If the socket = None, i.e. if it has not been
                             created using connect(), or has been disconnected
                             with disconnect()
            IOError - If network IO (request for or receipt of data) fails.
                    - If this is raised, the socket is probably not connected.
            OSError - If the server fails to retreive the file, or will not/
                      cannot receive it.
                    - e.g. if the file does not exist.
            ValueError - If it receives badly formatted data from the server.
                       - Should never happen if server is working properly.
        """
        #Thread requires a call to its constructor
        threading.Thread.__init__(self)
        
        self.download = download
        self.filename = filename
        self.file_object = file_object
        
        self.file_size = file_size
        self.bytes_transferred = 0
        #transfer_going - whether or not the transfer is in progress
        #false if finished, failed, or waiting in the queue
        self.transfer_going = False
        #has_failed indicates if the transfer has failed.
        self.has_failed = False
        self.is_complete = False
        self.has_started = False

        #for downloading, file needs to be written to in binary mode.
        if download and file_object.mode != "wb":
            raise AttributeError("File must be opened in wb mode for download")
        #for uploading, file needs to be read from in binary mode.
        elif not download and file_object.mode != "rb":
            raise AttributeError("File must be opened in rb mode for upload")
        
        if download:
            self.initialiseDownload()
        else:
            self.initialiseUpload()

        #If there is not currently a transfer in progress
        if not FileTransfer.transfer_in_progress:
            #There is a transfer in progress now
            FileTransfer.transfer_in_progress = True
            #Start the thread - thread handles actual data transfer.
            self.start()
        else:
            #there is a transfer already in progress, so add this one to the
            #queue
            FileTransfer.transfer_queue.put(self)
    #End of Constructor
    

    #getStatus method - to get a tuple of the transfer status
    def getStatus(self):
        """
        Usage:
            Use to keep track of the file transfer's status

        Returns:
            tuple of file transfer status:
                (bytes_transferred, file_size, transfer_going, has_failed,
                 is_complete, has_started)
        """
        status = (self.bytes_transferred, self.file_size, self.transfer_going,
                  self.has_failed, self.is_complete, self.has_started)
        return status
    #End of getStatus method


    #initialiseDownload method - to initialise for download (not upload)
    #This gets file size data from the server, and lets the server know to add
    #  this transfer to its queue.
    def initialiseDownload(self):
        """
        Usage:
            For internal use only.
            Used to initialise the FileTransfer object for a download.
            Communicates with server, gets file size data, lets server know to
            add this to its queue of transfers.

        Exceptions:
            AttributeError - If the socket = None, i.e. if it has not been
                             created using connect(), or has been disconnected
                             with disconnect()
            IOError - If network IO (request for or receipt of data) fails.
                    - If this is raised, the socket is probably not connected.
            OSError - If the server fails to retreive the file
                    - e.g. if the file does not exist.
            ValueError - If it receives badly formatted data from the server.
                       - Should never happen if server is working properly.
        """
        # command should be "DOWN|filename"
        command = DOWNLOAD_CMD + DIVIDER + self.filename
        data = sendCmdReceiveReply(command)
        #If server failed to get file.
        if checkForFailure(data):
            raise OSError("Server: Could not send file.")
        try:
            self.file_size = int(data[0])
        except ValueError:
            #Server has sent bad data. (data[0] should be data length integer)
            #Tell server to cancel transfer.
            sendMsg(CANCEL_CMD)
            raise ValueError("Bad data from server.")
        sendMsg(SUCCESS_MSG)
    #End of initialiseDownload method
    

    #initialiseUpload method - to initialise for upload (not download)
    #Tells server the filename and filesize, and lets it know to add this
    #transfer to its queue
    def initialiseUpload(self):
        """
        Usage:
            For internal use only.
            Used to initialise the FileTransfer object for an upload.
            Communicates with server, sends server data on the file being
            uploaded, lets server know to add this to its transfer queue.

        Exceptions:
            AttributeError - If the socket = None, i.e. if it has not been
                             created using connect(), or has been disconnected
                             with disconnect()
            IOError - If network IO (request for or receipt of data) fails.
                    - If this is raised, the socket is probably not connected.
            OSError - If the server will not/cannot receive file.
                    - e.g. if there is already a file with specified name.
            ValueError - If it receives badly formatted data from the server.
                       - Should never happen if server is working properly.
        """
        # command should be "UP|filename|file_size"
        # changing name from path/name to name:
        command = UPLOAD_CMD + DIVIDER + self.filename + DIVIDER \
                + str(self.file_size)
        message = sendCmdReceiveReply(command)
        #If server will not accept file upload.
        if checkForFailure(message):
            raise OSError("Server would not accept file.")
    #End of initialiseUpload method


    #transfer method - to carry out the file transfer (only call from run)
    def transfer(self):
        """
        Usage:
            For internal use only.
            Used to perform the actual transfer/read/write of data.

        Exceptions:
            AttributeError - If the transfer socket has not been created.
            IOError - If network IO (request for or receipt of data) fails.
                    - If this is raised, connection is dead.
        """
        try:
            #Loop until all data is transferred.
            while self.bytes_transferred < self.file_size:
                #if it's a download, receive data.
                if self.download:
                    #receive data through socket.
                    data = self.transfer_socket.recv(BUFFER_SIZE)
                    #if data == "", the transfer has failed.
                    if data == "" or data == None:
                        raise socket.error
                    self.bytes_transferred += len(data)
                    #write binary data to file
                    self.file_object.write(data)
                    self.file_object.flush()
                #If it's an upload, send data.
                else:
                    #read data from file, and send it through the socket
                    data = self.file_object.read(BUFFER_SIZE)
                    self.transfer_socket.send(data)
                    self.bytes_transferred += len(data)
        except (socket.error, socket.timeout):
            raise IOError("Transfer failed.")
    #End of transfer method


    #run method - required by thread class - code to be concurrently executed
    def run(self):
        """
        Usage:
            For internal use only.
            Required by thread class, code here is executed concurrently.
            This performs initialisation of the connection used for file
            transfer, and will automatically start the next transfer in the
            queue upon completion.
        """
        self.has_started = True
        try:
            #Create a socket and connect it using the file transfer port
            self.transfer_socket = socket.socket(socket.AF_INET,
                                                 socket.SOCK_STREAM)
            #Sleep for a short time to give server time to set up:
            time.sleep(0.2)
            self.transfer_socket.connect((address, TRANSFER_PORT_NUM))
            #Call actual transfer code
            self.transfer()
        except (IOError, socket.error, socket.herror, socket.gaierror,
                socket.timeout):
            #Some exception has been thrown, this transfer has failed.
            self.transfer_going = False
            self.has_failed = True
        else:
            #The transfer has completed without any issues.
            self.is_complete = True
        finally:
            #Tidying up - close file and socket once operations are done
            self.transfer_socket.close()
            self.file_object.close()
        
        try:
            #Get the next transfer in the queue
            next_transfer = FileTransfer.transfer_queue.get_nowait()
        except Queue.Empty:
            #if Queue.Empty is caught, it means there is nothing in the queue
            #because queue is empty, transfers are finished for now.
            FileTransfer.transfer_in_progress = False
        else:
            #start the next transfer in the queue
            next_transfer.start()
    #End of run method
    
#End of FileTransfer class


#Static fields for FileTransfer class
FileTransfer.transfer_queue = Queue.Queue()
FileTransfer.transfer_in_progress = False


#getFileText function - to get from the server the contents of a text file.
def getFileText(filename):
    """
    Usage:
        Requests that the server send text content for a file.
    
    Takes in:
        filename - The file name of the file whose contents are being
                   requested.
    
    Returns:
        String of text from the file.
    
    Exceptions:
        IOError - If network IO (request for or receipt of data) fails.
                - If this is raised, the socket is probably not connected.
        OSError - If the server has failed to get the file.
                - e.g. if the file does not exist.
        ValueError - If it receives badly formatted data from the server.
                   - This should never happen if server is working properly.
        AttributeError - If the socket = None, i.e. if it has not been created
                         using connect(), or has been disconnected with
                         disconnect()
    """
    try:
        #"GETTEXT|filename"-recognised by server
        command = GETTEXT_CMD + DIVIDER + filename
        data = sendCmdReceiveReply(command)
    except (IOError, AttributeError): raise
    
    #Server couldn't/wouldn't get file data.
    if checkForFailure(data):
        message = "Server: Could not get file."
        if len(data) >= 2:
            message = "Server: " + data[1]
        raise OSError(message)
    else:
        try:
            filesize = int(data[0])
        except ValueError:
            raise ValueError("Server sent bad filesize data.")
    
    sendMsg(CONTINUE_CMD)
    data_transferred = 0
    file_text = ""
    while data_transferred < filesize:
        try:
            data = receiveData()
            data_transferred += len(data)
            file_text += data
        except (IOError, AttributeError): raise
    return file_text
#End of getFileText function

###############################################################################
# End of file transfer code
###############################################################################




###############################################################################
# Internally used convenience/abstraction functions
###############################################################################

#sendCmdReceiveReply function - to send cmd to server and return response
def sendCmdReceiveReply(command, params=[]):
    """
    Usage:
        For internal use only.
        sends a command, with optional parameters, to the server and returns
        the server's response in a list, split by DIVIDER.
    
    Takes in:
        command - The command to send to the server.
        params - optional parameters to go with the command.

    Returns:
        Data from the server, separated into a list using DIVIDER to separate
        elements.

    Exceptions:
        IOError - If network IO (request for or receipt of data) fails.
                - If this is raised, the socket is probably not connected.
        AttributeError - If the socket = None, i.e. if it has not been created
                         using connect(), or has been disconnected with
                         disconnect()
    """
    for param in params:
        command += DIVIDER + param
    
    try:
        sendMsg(command, params)
    except (IOError, AttributeError): raise
    
    try:
        reply = receiveData()
    except (IOError, AttributeError): raise
    
    reply_list = reply.split(DIVIDER)
    return reply_list
#end of sendCmdReceiveReply function


#sendCmd function - to send cmd to server where no reply is expected
def sendMsg(command, params=[]):
    """
    Usage:
        For internal use only.
        sends a command, with optional parameters, to the server, does not wait
        for a response.
    
    Takes in:
        command - The command to send to the server.
        params - optional parameters to go with the command.
    
    Exceptions:
        IOError - If network IO (request for or receipt of data) fails.
                - If this is raised, the socket is probably not connected.
        AttributeError - If the socket = None, i.e. if it has not been created
                         using connect(), or has been disconnected with
                         disconnect()
    """
    #Compile command and params into one string:
    for param in params:
        #Remove all dividers from param - these will screw up parsing of data
        command = string.replace(command, DIVIDER, "")
        command += DIVIDER + param
    
    try:
        client_socket.send(command)
    except socket.error:
        #if connection error is detected, connection is broken so tidy up.
        disconnect(notify_server=False)
        raise IOError("Network IO failed.")
    except AttributeError:
        raise AttributeError("Socket has not been created.")
#end of sendCmd function


#receiveData function - to wait for data receipt without sending cmd
def receiveData():
    """
    Usage:
        For internal use only.
        Waits for server to send data, then returns data.
    
    Returns:
        Data from the server as a raw string.
    
    Exceptions:
        IOError - If network IO (request for or receipt of data) fails.
                - If this is raised, the socket is probably not connected.
        AttributeError - If the socket = None, i.e. if it has not been created
                         using connect(), or has been disconnected with
                         disconnect()
    """
    try:
        data = client_socket.recv(BUFFER_SIZE) #recieve bytes
        if data == "":
            raise socket.error
    except (socket.error, socket.timeout):
        #if connection error is detected, connection is broken so tidy up.
        disconnect()
        raise IOError("Network IO failed.")
    except AttributeError:
        raise AttributeError("Socket has not been created.")
    return data
#end of receiveData function


#checkForFailure function - to check if the server has sent failure message
def checkForFailure(data):
    """
    Usage:
        For internal use - Nothing will break if this is used, but there's no
        reason to use this externally.
        Checks if data from server contains failure message.
    
    Takes in:
        data - list of data from server.
    
    Returns:
        True - if the data is a failure message or is otherwise invalid.
        False - if the data is not a failure message
    """
    if (len(data) == 0) or (data[0] == FAILURE_MSG) or (data[0] == CANCEL_CMD):
        return True
    else:
        return False
#end of checkForFailure function

###############################################################################
# End of internal functions
###############################################################################

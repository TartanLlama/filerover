"""
ServerIO module deals with accepting connections from a client, listening for
commands/requests from the client, and responding to them.

Usage:
    Run as main:
    Command line parameters:
        first parameter: directory of filespace
        second parameter: mcast_on to enable multicasting
    or:
    Wait for connection using getConnection()
        - Blocks until recieves connection or encounters error.
    Listen for/respond to requests using serverLoop()
        - Blocks until the client disconnects or the connection fails.
    Force disconnect using disconnect()
    Do not use functions labelled as "For internal use"
    No other functions should be called outside of serverLoop()
        - These are for responding data to client requests, and will likely
          cause problems on the client side if used incorrectly.

Exceptions:
    In all functions except getConnection() and serverLoop(), all forseeable
    exceptions are handled and passed on to the client in the form of a failure
    message.
    IOError - may be raised by getConnection() or serverLoop() if a
    network/connection problem occurs.
    AttributeError - If serverLoop is started before getConnection() or after
                     disconnect().
"""
__author__ = "Sean O'Kelly <so227@st-andrews.ac.uk>"
__date__ = "2010-11-13  23:18"

import socket
import sys
import threading
import Queue

import fileviewer
import multicastsrv




###############################################################################
# Globals
###############################################################################

#Constants - same across client and server
PORT_NUM = 56740 #unique port number based on my unix user id
TRANSFER_PORT_NUM = 56744 #other group member's port number
BUFFER_SIZE = 8192 #8kB - enough for anything like directory listing etc.
TIMEOUT = 30 #30 seconds (client only, included for completeness)
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
client_socket = None
multicaster = None

###############################################################################
# End of globals
###############################################################################





###############################################################################
# Functions to get/end the connection
###############################################################################

#getConnection function: waits for connection from a client
def getConnection():
    """
    Usage:
        Use to initialise the connection to the client before attempting to use
        this module. This function will block until it recieves a connection or
        an error occurs.

    Exceptions:
        IOError - If the function fails to connect or fails to bind the socket.
    """
    try:
        print "Listening for connection..."
        #AF_INET and SOCK_STREAM - constants defining type of socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #Set up socket so that the address can be reused:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #next: bind server_socket to PORT_NUM on current machine
        server_socket.bind((socket.gethostname(), PORT_NUM))
        #Allow only first connection
        server_socket.listen(1)
        global client_socket
        (client_socket, address) = server_socket.accept()
        print "Connected"
    except socket.error as e:
        print "Connection failed"
        print e
        raise IOError("Connection failed")
    finally:
        #Tidy up by closing unused socket
        server_socket.close()
#end of getConnection function


#disconnect function: used to force disconnect
def disconnect():
    """
    Usage:
        Mainly for internal use in some exceptional circumstances, and to tidy
        up at the end.
        Use to force the server to disconnect. Normally, the server will wait
        until the client disconnects. The client does not expect the server to
        disconnect, and does not listen for disconnect commands, so this should
        only be used to force a disconnect.
    """
    global client_socket
    if client_socket != None:
        client_socket.close()
        #Remove reference to old socket object.
        client_socket = None
        print "Disconnected"
#end of disconnect function

###############################################################################
# End of connection functions
###############################################################################





###############################################################################
# serverLoop
###############################################################################

#serverLoop function: awaits commands/requests from the client
def serverLoop():
    """
    Usage:
        Accepts commands, in a loop, from the client and responds to them.
        Once a connection has been established, this may be used to listen for
        and respond to requests from the client.
        serverLoop() will block until the connection fails or is closed by the
        client.

    Exceptions:
        AttributeError - If the function is called before the socket is
                         connected, or after it has disconnected.
    """
    if client_socket == None:
        raise AttributeError("Socket not initialised")
    
    print "Listening for messages..."
    while True: #Keep listening for messages until disconnect
        
        print "\n"
        
        try:
            message = client_socket.recv(BUFFER_SIZE)
            if message == "":
                # "" = client disconnect/network failure
                raise socket.error
        except socket.error:
            print "Error getting request, breaking from loop."
            # if socket.error is raised, the connection is probably dead
            break
        
        
        print "Recieved: " + message
        # message = "COMMAND|params"
        request_and_params = message.split(DIVIDER)
        request = request_and_params[0]
        #The string to send back to the client:
        response = ""
        
        
        #Change directory
        if request == CHDIR_CMD and len(request_and_params) >= 2:
            print "Changing directory..."
            path = request_and_params[1]
            response = chDir(path)
        
        #List directory
        elif request == LISTDIR_CMD:
            print "Listing directory..."
            response = listDir()
        
        #Get current directory
        elif request == GETDIR_CMD:
            print "Returning current working directory..."
            response = getCWD()
        
        #Get file properties
        elif request == GETINFO_CMD and len(request_and_params) >= 2:
            print "Returning file info..."
            filename = request_and_params[1]
            response = getFileProperties(filename)
        
        #Create a directory
        elif request == MKDIR_CMD and len(request_and_params) >= 2:
            print "Creating directory..."
            dir_name = request_and_params[1]
            response = makeDir(dir_name)
        
        #Transfer text contents of file
        elif request == GETTEXT_CMD and len(request_and_params) >= 2:
            print "Sending text data to client..."
            filename = request_and_params[1]
            sendTextContents(filename)
            #All communication handled inside function, skip reply.
            continue
        
        #Send file to client
        elif request == DOWNLOAD_CMD and len(request_and_params) >= 2:
            print "Sending file to user..."
            filename = request_and_params[1]
            transfer = FileTransfer(filename, receiving=False)
            #Don't send a response, all communication has been handled within
            #sendFile function.
            continue
        
        #Receive file from client
        elif request == UPLOAD_CMD and len(request_and_params) >= 3:
            print "Getting file from user..."
            filename = request_and_params[1]
            filesize = request_and_params[2]
            transfer = FileTransfer(filename, receiving=True,
                                    filesize_string=filesize)
            #Don't send a response, all communication has been handled within
            #sendFile method.
            continue
        
        #Disconnect command
        elif request == DISCONNECT_CMD:
            #break from listening for commands
            break
        
        #Request not recognised
        else:
            #Notify client of failure.
            response = FAILURE_MSG + DIVIDER + "Did not recognise command."
        
        #replying...
        print "Replying:"
        print response
        try:
            client_socket.send(response)
        except socket.error:
            print "Error sending response, breaking from loop."
            # if socket.error is raised, the connection is probably dead
            break
        
        print "\n"
    
    #disconnect - to tidy up afterwards
    disconnect()
#end of serverLoop function
    
###############################################################################
# End of serverLoop
###############################################################################





###############################################################################
# Internally used functions to respond to client requests
###############################################################################

#chDir function - changes directory, is called by client
def chDir(path):
    """
    Usage:
        For internal use only.
        Should only be used to respond to client request. i.e. in serverLoop()
        Changes directory to specified path.
    
    Takes in:
        path - path which client has requested to change to.
    
    Returns:
        - SUCCESS_MSG if the operation is carried out succesfully.
        - FAILURE_MSG (with parameters) if operation fails.
    """
    try:
        fileviewer.executeCommands(path)
        response = SUCCESS_MSG
    except fileviewer.NavigationException as e:
        response = FAILURE_MSG + DIVIDER + str(e)
    except (OSError, fileviewer.CommandException):
        response = FAILURE_MSG + "|Invalid directory change."
    return response
#end of chDir function


#makeDir function - to create a directory at the client's request
def makeDir(path):
    """
    Usage:
        For internal use only.
        Should only be used to respond to client request. i.e. in serverLoop()
        Creates a new directory within the current directory.
    
    Takes in:
        path - path of new directory.
    
    Returns:
        - SUCCESS_MSG if the operation is carried out succesfully.
        - FAILURE_MSG (with parameters) if operation fails.
    """
    try:
        fileviewer.createDir(path)
        response = SUCCESS_MSG
    except OSError:
        response = FAILURE_MSG + "|Invalid directory"
    return response
#end of makeDir function


#listDir function - returns string of files/folders in directory
def listDir():
    """
    Usage:
        For internal use only.
        Should only be used to respond to client request. i.e. in serverLoop()
        Should be called if user requests the directory list.
        Should never fail under normal circumstances.
    
    Returns:
        - String of directory listing in the form: "|file1|size1\\nfile2|size2"
          etc. (Generates this from a list of tuples).
        - FAILURE_MSG with parameter if it could not list the directory for
          some reason.
    """
    try:
        dir_list = fileviewer.executeCommands(".")
        #dir_list = [("filename1", size1), ("filename2", size2)] etc.
    except (OSError, fileviewer.CommandException):
        response = FAILURE_MSG + "|Failed to retrieve data."
        return response
    
    response = "|"
    for (name, size) in dir_list:
        #separate tuple elems with "|", list elems with "\n"
        response += name + "|" + str(size) + "\n"
    return response
#end of listDir function


#getCWD function - returns path to current working directory
def getCWD():
    """
    Usage:
        For internal use only.
        Should only be used to respond to client request. i.e. in serverLoop()
        Should be called if user requests the path to the current directory.
        Should never fail under normal circumstances.

    Returns:
        - String of the path to the current directory
        - FAILURE_MSG with parameter if it could not get the current directory
          for some reason.
    """
    try:
        response = fileviewer.getPwd()
    except OSError:
        response = FAILURE_MSG + "|Failed to retrieve path."
    return response
#end of listDir function


#getFileProperties function - returns properties of a file
def getFileProperties(filename):
    """
    Usage:
        For internal use only.
        Should only be used to respond to client request. i.e. in serverLoop()
        Should be called if user requests details on a file.

    Takes in:
        filename - File name for file which the client has requested details

    Returns:
        - String of file properties in the form "data1|data2|data3|data4"
        - FAILURE_MSG with parameter if the file cannot be accessed
    """
    try:
        (path, size, last_access, last_mod) = \
                fileviewer.executeCommands(filename)
        response = path + "|" + str(size) + "|" + str(last_access) + "|" \
                + str(last_mod)
    except (OSError, fileviewer.CommandException):
        response = FAILURE_MSG + "|Could not access file."
    return response
#end of getFileProperties function

###############################################################################
# End of internal functions for client requests
###############################################################################




###############################################################################
# Code for file transfer (FileTransfer class)
###############################################################################

#FileTransfer class - allows concurrent, queued (one at a time) file transfer
class FileTransfer(threading.Thread):
    """
    Usage:
        For internal use only (in response to client download/upload request)
        File transfers run concurrently and on a different, so this will not
        block or disrupt the request/response loop.
        This should not be created (or any functions called) outside of
        serveLoop().
    """
    
    #Constructor
    def __init__(self, filename, receiving=False, filesize_string=None):
        """
        Constructor

        Usage:
            For internal use only.
            For an upload:
                my_transfer = Transfer(filename_to_save_as,
                                       receiving=True,
                                       filesize_string=string_of_filesize)
            For a download:
                my_transfer = Transfer(filename_of_file_to_download,
                                       file_object_to_write_to)
        
        Takes in:
            filename - If this transfer is an upload, the filename is the name
                       to save the uploaded file to on the server.
                       If this is a download, it is the name of the file to
                       download from server.
            download - Boolean for whether we are sending or receiving a file.
                       should be True if this is an upload from the client,
                       False (default) for a download to the client.
            filesize_string - If this is an upload from client to server, this
                              is required, and must be a string (from the
                              client) of the exact size of the file in bytes.
                              If this is a download, this is not required and
                              will be ignored.
        """
        threading.Thread.__init__(self)
        
        self.receiving = receiving
        self.filename = filename
        self.file_object = None
        
        self.file_size = filesize_string
        self.bytes_transferred = 0

        self.has_failed = False
        
        try:
            print "Communicating with client..."
            if receiving:
                self.initialiseReceipt()
            else:
                self.initialiseSend()
            print "Communication succesful."
        except (ValueError, OSError, IOError):
            #There has been some kind of error, initialise methods will have
            #attempted to notify client of this. Unless the connection is dead,
            #we can resume normal operation.
            print "Communication unsuccesful"
            return
        
        #If there is not already a transfer in progress...
        if not FileTransfer.transfer_in_progress:
            #start the transfer
            print "There are no transfers in progress"
            print "Starting transfer"
            FileTransfer.transfer_in_progress = True
            self.start()
        else:
            print "There is a transfer already in progress"
            print "Adding transfer to queue"
            #There is a transfer in progress already, so add to the queue...
            FileTransfer.transfer_queue.put(self)
            print "Queue length: " + str(FileTransfer.transfer_queue.qsize())
    #End of Constructor
    
    
    #initialiseSend method - to initialise this to send a file to the client
    def initialiseSend(self):
        """
        Usage:
            For internal use only, and only if this object is a download.
        
        Exceptions:
            OSError - If the file cannot be accessed
            IOError - If network communication fails
        """
        try:
            #Access the file to send.
            (self.file_object, self.file_size) = \
                    fileviewer.getFile(self.filename)
        except OSError as e:
            #Try to send a failure message to the client.
            message = FAILURE_MSG + "|" + str(e)
            client_socket.send(message)
            raise
                
        try:
            #Send file size to client - client will be expecting this.
            client_socket.send(str(self.file_size))
            #Client will respond with SUCCESS_MSG or CANCEL_CMD
            message = client_socket.recv(BUFFER_SIZE)
        except socket.error:
            #closing unnecessary file:
            self.file_object.close()
            raise IOError("Network IO failed")
        
        #Check if the client has succesfully initialised
        if message != SUCCESS_MSG:
            raise IOError
    #End of initialiseSend method
    
    
    
    #initialiseReceipt method - to initialise for receiving from the client
    def initialiseReceipt(self):
        """
        Usage:
            For internal use only, and only if this object is an upload.
        
        Exceptions:
            OSError - If the file cannot be accessed
            ValueError - If the data from the client is bad
            IOError - If network communication fails
        """
        try:
            self.file_size = int(self.file_size)
            self.file_object = fileviewer.createFile(self.filename)
        except (ValueError, OSError) as e:
            try:
                #Try to send a failure message to the client.
                message = FAILURE_MSG + "|" + str(e)
                client_socket.send(message)
                raise
            except socket.error:
                #If there is a connection problem at the same time
                raise IOError("Network IO failed.")
        try:
            #Client is waiting for continue command
            client_socket.send(SUCCESS_MSG)
        except socket.error:
            #IO with client has failed, connection is probably dead.
            #closing unnecessary file:
            self.file_object.close()
            raise IOError("Network IO failed.")
    #End of initialiseReceipt method
    
    
    #transfer method - to carry out data transfer/file operations
    def transfer(self):
        """
        Usage:
            For internal use only.
            Used to perform the actual transfer/read/write of data.
        
        Exceptions:
            IOError - If network communication fails
        """
        try:
            #Loop until all data is transferred.
            while self.bytes_transferred < self.file_size:
                #if it's an upload, receive data.
                if self.receiving:
                    #receive data through socket.
                    data = self.transfer_socket.recv(BUFFER_SIZE)
                    #if data == "", the transfer has failed.
                    if data == "" or data == None:
                        raise socket.error
                    self.bytes_transferred += len(data)
                    #write binary data to file
                    self.file_object.write(data)
                    self.file_object.flush()
                #if it's a download, send data.
                else:
                    #read data from file, and send it through the socket
                    data = self.file_object.read(BUFFER_SIZE)
                    self.transfer_socket.send(data)
                    self.bytes_transferred += len(data)
        except (socket.error, socket.timeout):
            raise IOError("Transfer failed.")
    #End of transfer method
    
    
    #run method - required by Thread - code here is concurrently executed
    def run(self):
        """
        Usage:
            For internal use only.
            Required by thread class, code here is executed concurrently.
            This performs initialisation of the connection used for file
            transfer, and will automatically start the next transfer in the
            queue upon completion.
        """
        try:
            #Create a server socket to accept a connection
            self.listen_socket = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM)
            #Set up socket so that the address can be reused:
            self.listen_socket.setsockopt(socket.SOL_SOCKET,
                                          socket.SO_REUSEADDR, 1)
            self.listen_socket.bind((socket.gethostname(), TRANSFER_PORT_NUM))
            self.listen_socket.listen(1)
            #transfer_socket is only used for file transfer.
            (self.transfer_socket, addr) = self.listen_socket.accept()
            self.listen_socket.close()
            #begin data transfer
            self.transfer()
            self.transfer_socket.close()
            self.file_object.close()
        except IOError:
            #some error has occured in file transfer, stop this transfer and
            #move on.
            self.has_failed = True
        finally:
            try:
                #Get the next transfer in the queue
                next_transfer = FileTransfer.transfer_queue.get_nowait()
            except Queue.Empty:
                #queue is empty, so there are no more transfers for now.
                FileTransfer.transfer_in_progress = False
            else:
                #start the next transfer.
                next_transfer.start()
            finally:
                if self.receiving:
                    message_str = "Upload "
                else:
                    message_str = "Download "
                if self.has_failed:
                    message_str += "failed: "
                else:
                    message_str += "complete: "
                message_str += self.filename
                print message_str
    #End of run method
    
#End of FileTransfer class


#Static fields for FileTransfer class
FileTransfer.transfer_queue = Queue.Queue()
FileTransfer.transfer_in_progress = False


#getTextContents function - returns text contents of a file
def sendTextContents(filename):
    """
    Usage:
        For internal use only.
        Should only be used to respond to client request. i.e. in serverLoop()
        Should be called if user requests text contents of a file.
        All communication of data is handled in this function.
    
    Takes in:
        filename - File name for file which the client has requested details
    """
    try:
        try:
            print "Getting file contents..."
            file_text = fileviewer.getFileContents(filename)
        except OSError as e:
            print "Failed, notifying client..."
            client_socket.send(FAILURE_MSG + DIVIDER + str(e))
            return
        else:
            print "Sending filesize..."
            filesize = len(file_text)
            client_socket.send(str(filesize))
            reply = client_socket.recv(BUFFER_SIZE)
            if reply != CONTINUE_CMD:
                return
            data_sent = 0
            while data_sent < filesize:
                lower = data_sent
                upper = data_sent + BUFFER_SIZE
                if upper > filesize:
                    upper = filesize
                data = file_text[lower:upper]
                client_socket.send(data)
                data_sent += len(data)
                print "Sent " + str(data_sent) + " of " + str(filesize) + \
                      " bytes."
    except socket.error:
        print "Socket error."
        return
#End of getTextContents function

###############################################################################
# End of file transfer code
###############################################################################




###############################################################################
# Main
###############################################################################

def main():
    multicaster = multicastsrv.MulticastThread()
    try:
        custom_root = ""
        if len(sys.argv) >= 2:
            custom_root = sys.argv[1]
            print "Setting root to command line parameter: " + custom_root
        else:
            print "Using default root."
        print "Starting multicaster..."
        multicaster.start()
        while True:
            if custom_root != "":
                fileviewer.setRoot(custom_root)
            getConnection()
            print "Stopping multicaster."
            serverLoop()
            print "Resetting..."
            reload(fileviewer)
    except KeyboardInterrupt:
        print "\nExiting..."
    finally:
        multicaster.stop()

if __name__ == "__main__":
    main()

###############################################################################
# End of main
###############################################################################

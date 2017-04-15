"""The GUI for the fileRover program"""

import sys
import clientio
import fileviewer
import multicastcli
import socket
import threading
import time
from Tkinter import *



keywordDic = ["connect","disconnect","exit","cd","cdserver","mkdir","mkdirserver","serverlist","help"]


class Application(Frame):
    connected = False
    lastCommand = ""
	
    def repaint(self):
        """Updates all text fields etc."""
        
        #update the contents of the client's pwd
	clientList = fileviewer.getPwdContents()
	self.setDirList(True,clientList)

        #update the client's pwd path
	clientDirectory = fileviewer.getPwd()
	self.setClientDirEntry(clientDirectory)

	if self.connected:
                #update the contents of the server's pwd
		serverList = clientio.listDir()
		self.setDirList(False,serverList)

                #update the server's pwd path
		serverDirectory = clientio.getDir()
		self.setServerDirEntry(serverDirectory)
        else:
		self.serverList.delete(0,END)   
		self.serverDir.delete(0,END) 
   
        #reset the command line
	self.commandLine.delete(0,END)

    def contains(self, item, userStr):
        """Returns the item if the user string is a substring of it, otherwise returns the user string"""

	if userStr in item:
		return item
	return userStr
		
    def autoComplete(self, event):
        """Attempts to autocomplete the contents of the command line with a valid command"""
	userString = self.getCommandLine()
	suggestion = ""
	for item in keywordDic:
		suggestion  = self.contains(item,userString)
		if suggestion != userString:
			self.commandLine.delete(0,END)
			self.setCommandLine(suggestion)
			break
        return 'break'

    def connectToServer(self, ip):
        """Connects to a server
        
        If no address is given, connect to the local host"""

	failed = False
	isLocal = True
        
        #connects to the local host if no address is specified
	if ip == '':
            self.setCommandHistory("Connecting to localhost")
            try:
                clientio.connect(socket.gethostname())
            except:
                failed = True

        #otherwise try and connect to the given ip address
	else:
	    isLocal = False
            try:
                clientio.connect(ip)
		
            except:
                failed = True

	if failed:	
            self.setCommandHistory("Connection Failed")
            
        #cleanup the GUI and display messages
	else:
            self.connected = True
	    self.connectBtn["text"] = "Disconnect"
            self.connectBtn["command"] = self.disconnectFromServer
	    message = "Connection Established"
	    if isLocal == False:
		message = message + " to IP: " + ip
            self.setCommandHistory(message)
            serverList = clientio.listDir()
            self.setDirList(False,serverList)
            self.repaint()

    def disconnectFromServer(self):
        """Disconnects from the server you are connected to"""

	failed = False
        
        if self.connected:
            clientio.disconnect()

            #cleanup GUI and display messages
            self.setCommandHistory("Disconnected from Server")
            self.connectBtn["text"] = "Connect"
            self.connectBtn["command"] = self.connect
            self.connected = False
            self.serverList.delete(0,END)
            self.setServerDirEntry("Not connected")
        else:
            self.setCommandHistory("Not connected to a server")

    def cdClient(self, folder):
        """Change the pwd on the client"""
        folder = self.listToString(folder)
        try:
            fileviewer.executeCommands(folder)
            self.setCommandHistory("Changing dir to: "+folder)
            self.repaint()
        except OSError, error:
            self.setCommandHistory(str(error))
            fileviewer.executeCommands('..') #ensures the fileviewer thinks that you are in the correct directory
        except fileviewer.CommandException, error:
            self.setCommandHistory(str(error))
        self.repaint()

    def cdServer(self,folder):
        """Change the pwd on the server"""
        folder = self.listToString(folder)
        try:
            clientio.chDir(folder)
            self.setCommandHistory("Changing Server dir to: "+folder)

	except IOError:
	    self.setCommandHistory("No response from Server - reconnect")
	    self.connected = False
        except OSError:
            self.setCommandHistory(str(error))
            if str(error) == 'Server: Failed to retrieve data.':
                clientio.chDir('..') #ensures the fileviewer thinks that you are in the correct directory
	except Exception, error:
	    self.setCommandHistory(str(error))
	    
       	self.repaint()

    def listToString(self, list):
        out = ''
        for x in list:
            out += x + ' '
            
        return out[:-1]
    
    def clientMakeDirCmd(self,dir):
        """Make a directory on the client from a command line request"""

	dir = self.listToString(dir)
        self.clientMakeDir(dir)

    def serverMakeDirCmd(self,dir):
        """Make a directory on the server from a command line request"""
        dir = self.listToString(dir)
        self.serverMakeDir(dir)

    def getHistoryCommand(self,event):
        """Connects to the server if you double click on a member of the server list"""
	command = self.getCommandHistory()
	commandList = command.rsplit(" ")
	if self.connected == False and commandList[0] == "Server":
            self.connectToServer(commandList[1])
 
		
    def getServerList(self):
        """Finds a list of servers which are running and displays it"""
        multicastcli.setUp()	
	ipList = multicastcli.discover()

	if len(ipList) > 0:
            for x in ipList:
                self.setCommandHistory("Server "+x)
	else:
            self.setCommandHistory("No servers are currently running")

    def performAction(self, commandList):
        """Performs actions based on commands from the command line"""

	if commandList[0] == "connect":
            if len(commandList) > 1:
                self.connectToServer(commandList[1])	
            else:
                self.connectToServer('')

	elif commandList[0] == "exit":
            sys.exit()

	elif commandList[0] == "disconnect":
            self.disconnectFromServer()
	    
	elif commandList[0] == "cd":
            self.cdClient(commandList[1:])

	elif commandList[0] == "cdserver":
            self.cdServer(commandList[1:])

	elif commandList[0] == "mkdir":
            self.clientMakeDirCmd(commandList[1:])

	elif commandList[0] == "mkdirserver":
            self.serverMakeDirCmd(commandList[1:])

	elif commandList[0] == "serverlist":
            self.getServerList()

	elif commandList[0] == "help":
		self.printHelp()

        self.repaint()

    def printHelp(self):
        """Prints the help message in the command history box"""

	helpCommand = [
		"=====================================================",
		"=====================================================",
		"connect - connect to local host",
		"connect IP - connect to a server ip",
		"disconnect - disconnect from server",
		"exit - close fileRover",
		"cd - change directory on your machine",
		"cdserver - change the directory on the server",
		"mkdir - make a directory on your machine",
		"mkdirserver - make a directory on the server",
		"serverlist - show a list of currently running servers",
		"=====================================================",
		"====================================================="
	]
	for x in helpCommand:
		self.setCommandHistory(x)

    def parseCommand(self,command):
        """Attempts to parse a command from the command line"""

	isValid = False
        commandList = command.split(" ")

        #check the first word of the command against the dictionary and perform the necessary action
        for x in keywordDic:
            if commandList[0] == x:
                isValid = True
                self.lastCommand = command
                self.performAction(commandList)

	if isValid == False:
            str = "Invalid command>> "+command+" << type help for help"
            self.setCommandHistory(str)
                
    def parseCommandEvent(self,event):
        """Deals with a command line command being input"""

        s = self.getCommandLine()
	if len(s) > 0: 
            self.commandLine.delete(0,END)
            self.parseCommand(s)
	else:
            self.setCommandLine(self.lastCommand)
	
	
    
    def setCommandHistory(self, command):
        """Adds to the command history"""

	self.commandHistory.insert(0,command)	

    def getCommandHistory(self):
        """Get the selected (highlighted) command history String"""

	index = self.commandHistory.curselection()[0]
        data = self.commandHistory.get(index)
        return data


    def setCommandLine(self,command):
        """Set the console command"""
	self.commandLine.insert(0,command)


    def setClientDirEntry(self,dir):
        """Set the pwd path for the client"""
        self.clientDir.delete(0,END)
        self.clientDir.insert(0,dir)

    def setServerDirEntry(self,dir):
        """Set the pwd path for the server"""
        self.serverDir.delete(0,END)
        self.serverDir.insert(0,dir)	

    def getCommandLine(self):
        """Return the string in the command line"""
        return self.commandLine.get()

    def getClientItem(self):
        """Return the selected client object"""
        index = self.clientList.curselection()[0]
        data = self.clientList.get(index)
        return data
    
    def getClientItemEvent(self,event):
        """Called when the user clicks on a client file/folder"""
        item = self.getClientItem()	
        item = item.split(" ")
        if len(item) > 0:
            if item[-1] == "": #if the item is a directory
                self.cdClient(item[:-1])
            else:
                self.displayFileText(self.listToString(item[:-1]))

    class TextPopup(object):
        """A popup box for displaying text"""

        def __init__(self, filename, file_contents):
            self = Tk()
            self.title(filename)

            self.scrollbar = Scrollbar(self)
            self.scrollbar.pack(side=RIGHT, fill=Y)

            self.w = Text(self, yscrollcommand=self.scrollbar.set)
            self.w.insert(INSERT, file_contents)
            self.w.configure(state=DISABLED)
            
            self.scrollbar.config(command=self.w.yview)
            
            self.w.pack()

    def displayFileText(self,filename):
        """Make a popup box displaying the text held in the given file on the client"""

        try:
            text = fileviewer.getFileContents(filename)
            popup = self.TextPopup(filename, text)

        except Exception, error:
            self.setCommandHistory(str(error))
  
       
    def getServerItem(self):
        """Return the selected server object"""
	try:
            index = self.serverList.curselection()[0]
            data = self.serverList.get(index)
            return data
	except:
            return ""

    def getServerItemEvent(self, event):
        """Called when the user double clicks on a server file/folder; carries out the correct action"""
        item = self.getServerItem()
       
        if len(item) > 0:
	    item = item.split(" ")
            if item[-1] == "": #if the item is a directory
                self.cdServer(item[:-1])
            #otherwise try and display the text of the file
            else:
                try:
                    text = clientio.getFileText(self.listToString(item[:-1]))
                    popup = self.TextPopup(self.listToString(item[:-1]), text)

                except Exception, error:
                    self.setCommandHistory(str(error))
                

    def setDirList(self,isClient,list):
        """Fill the client/server listbox with a list"""
	if isClient == True:
            self.clientList.delete(0,END)
	else:
            self.serverList.delete(0,END)

	for x in list:
            if len(x) > 0:
                s = ""
                if x[1] == -1: #if the filesize is -1, hence x is a directory	
                    s = x[0] + " " #print just the directory name
                else:
                    s = x[0] + " " + str(x[1]) #print the filename and the filesize

                if isClient == True:
                    self.clientList.insert(END,s)
                else:
                    self.serverList.insert(END,s)

    class ProgressBarUpdater (threading.Thread):
        """A thread to track transfer progress"""
        def __init__(self, progress_bar, transfer, message_writer, filename, transfer_type):
            threading.Thread.__init__(self)
            self.progress_bar = progress_bar
            self.transfer = transfer
            self.message_writer = message_writer
            self.filename = filename
            self.transfer_type = transfer_type
            self.start()

        def run(self):
            self.message_writer('Queing transfer')
            started = False
            #check if the download has started
            while not started:
                time.sleep(0.1)
                state = self.transfer.getStatus()
                started = state[5] #transfer_started
                
            self.message_writer(self.transfer_type + ': ' + self.filename)

            #if it has, initialize some data...
            transferring = True
            self.progress_bar.configure(label=self.transfer_type + ': ' + self.filename)
            #...and begin tracking it's progress
            while transferring:
                time.sleep(.1)
                state = self.transfer.getStatus()
                percent_done = float(state[0])/state[1]*100

                self.progress_bar.configure(state=NORMAL)
                self.progress_bar.set(percent_done)
                self.progress_bar.configure(state=DISABLED)

                if state[3] or state[4]: #transfer_complete or has_failed
                    transferring = False

            self.message_writer('Transfer of ' + self.filename + ' complete')

            self.progress_bar.configure(state=NORMAL)
            self.progress_bar.set(0)
            self.progress_bar.configure(state=DISABLED)

            self.progress_bar.configure(label='Progress')
        
               
    def uploadFile(self):
        """Uploads the selected file to the server

        Called when the upload button is pressed"""

	if self.connected:
            clientFile = self.getClientItem()
            clientFile = clientFile.split(" ")
            serverDir = clientio.getDir()

            if len(clientFile) > 1:
                name = self.listToString(clientFile[:-1])
                f = fileviewer.getFile(name)[0] #gets just the file, not the size as well
                fileSize = int(clientFile[-1])
                
                uploadObj = clientio.FileTransfer(name,f,fileSize,False)
                                
                updater = self.ProgressBarUpdater(self.progressBar, uploadObj, self.setCommandHistory, name, 'Uploading')
                    
        else:
            self.setCommandHistory('Not connected to a server')
            

    def downloadFile(self):
        """Downloads a file from the server

        Called when the download button is pressed"""

	if self.connected:
            serverFile = self.getServerItem()
            serverFile = serverFile.split(" ")
            clientDir = fileviewer.getPwd()

            if len(serverFile) > 1:
                name = self.listToString(serverFile[:-1])
                f = fileviewer.createFile(name)
                fileSize = int(serverFile[-1])
                
                downloadObj = clientio.FileTransfer(name,f,fileSize,True)
                                
                updater = self.ProgressBarUpdater(self.progressBar, downloadObj, self.setCommandHistory, name, 'Downloading')
        else:
            self.setCommandHistory('Not connected to a server')


    def clientBackDir(self):
        """Goes up one directory on the client

        Called when the client back button is pressed"""
        try:
            fileviewer.executeCommands("..")
            self.setCommandHistory("Moving up directory")
        except Exception, error:
            self.setCommandHistory(str(error))

	self.repaint()
	
    def serverBackDir(self):
        """Goes up one directory on the client

        Called when the client presses the server back button"""

        try:
            clientio.chDir("..")
            self.setCommandHistory("Moving up Servers directory")
	except IOError:
	    self.setCommandHistory("No response from Server - reconnect")
	    self.connected = False
	except Exception, error:
	    self.setCommandHistory(str(error))
	
	self.repaint()
        
    def clientMakeDirButton(self):
        """Creates a directory on the client
        
        Called when the client presses the make dir button"""

        dir = self.getCommandLine()
        if len(dir) == 0:
            self.setCommandHistory("Enter a valid name")
        else:		
	    self.clientMakeDir(dir)

    def clientMakeDir(self,dir):
        """Creates a directory on the client"""
        print dir
        try:
            fileviewer.createDir(dir)
            self.setCommandHistory("Made dir: "+dir)
        except Exception, error:
            self.setCommandHistory(str(error))

            self.repaint()

    def serverMakeDirButton(self):
        """Creates a directory on the server when the make dir button is pressed"""
	if self.connected:
        	dir = self.getCommandLine()
        	if len(dir) == 0:
            		self.setCommandHistory("Enter a valid name")
        	else:
            		self.serverMakeDir(dir)
	else:
		self.setCommandHistory("Connect to a Server")
	   
    def serverMakeDir(self,dir):
        """Creates a directory on the server"""
        try:
            clientio.makeDir(dir)
            self.setCommandHistory("Server making dir: "+dir)
	except IOError:
	    self.setCommandHistory("No response from Server - reconnect")
	    self.connected = False
        except Exception, error:
            self.setCommandHistory(str(error))

        self.repaint()
       
    def getIP(self):
        """Returns the contents of the ipEntry field for convenience"""
	return self.ipEntry.get()

    def connect(self, ipStr = ''):
        """A wrapper for connecting to the server"""

	ipStr = self.getIP()
 	self.connectToServer(ipStr)

    def clearHistoryList(self):
        """Clears the command history"""
	self.commandHistory.delete( 0, END)

    def createWidgets(self):
        """Creates all the necessary widgets for the GUI"""

	self.ipEntry = Entry(self,width=15)
	self.ipEntry.insert(0,"")
        self.ipEntry.bind('<Return>', self.connect)
	self.ipEntry.grid(row=0,column=0,sticky=W)

	self.connectBtn = Button(self)
	self.connectBtn["text"] = "Connect"
	self.connectBtn["command"] = self.connect
	self.connectBtn.grid(row=0)

	self.refreshBtn = Button(self)
	self.refreshBtn["text"] = "Refresh"
	self.refreshBtn["command"] = self.repaint
	self.refreshBtn.grid(row=0,sticky=E)

	self.progressBar = Scale(self, orient=HORIZONTAL, state=DISABLED, label='Progress', sliderlength=2, length=300)
	self.progressBar.grid(row=6, sticky=W)
        
	self.clearScrBtn = Button(self)
	self.clearScrBtn["text"] = "Clear History"
	self.clearScrBtn["command"] = self.clearHistoryList
	self.clearScrBtn.grid(row=0,column=1)

	self.showServerListBtn = Button(self)
	self.showServerListBtn["text"] = "Show Servers"
	self.showServerListBtn["command"] = self.getServerList
	self.showServerListBtn.grid(row=0,column=1,sticky=E)

	## allows the user to use commands
	self.commandLine = Entry(self,width=100)
	self.commandLine.bind("<Return>", self.parseCommandEvent)
	self.commandLine.bind("<Tab>", self.autoComplete)
	self.commandLine.insert(0,"")
	self.commandLine.grid(row=1,column=0,sticky=N,columnspan=2)
    	
	## create command history scrollbar
	self.historyScroll = Scrollbar(self)
	self.historyScroll.grid(row=2,column=2,sticky=W+S+N)
       

	## shows the users commands
    	self.commandHistory = Listbox(self,width=100)
    	self.commandHistory.insert(END, "")
	self.commandHistory.config(yscrollcommand=self.historyScroll.set)
	self.historyScroll.config(command=self.commandHistory.yview)
    	self.commandHistory.bind('<Double-1>', self.getHistoryCommand)
	self.commandHistory.grid(row = 2,columnspan=2)
    	
	## create the current director box
	self.clientDir = Entry(self,width=50)
	self.clientDir.insert(0,"client dir")
	self.clientDir.grid(row = 3, column = 0,sticky=W)
	
	## create the servers current directory box
	self.serverDir = Entry(self,width=50)
	self.serverDir.insert(0,"")
	self.serverDir.grid(row=3,column=1,sticky=W)

	self.clientScroll = Scrollbar(self)
	self.clientScroll.grid(row=4,column=0,sticky=E+S+N)
	
	## create the client file directory box
    	self.clientList = Listbox(self,width = 48)
    	self.clientList.insert(END,"")
	self.clientList.config(yscrollcommand=self.clientScroll.set)
	self.clientScroll.config(command=self.clientList.yview)
	self.clientList.bind('<Double-1>', self.getClientItemEvent)
	self.clientList.grid(row = 4, column=0,sticky=W)
    	
	self.serverScroll = Scrollbar(self)
	self.serverScroll.grid(row=4,column=2,sticky=E+S+N)
	
	## create the server file directory box
    	self.serverList = Listbox(self,width=50)
    	self.serverList.insert(END,"")
	self.serverList.config(yscrollcommand=self.serverScroll.set)
	self.serverScroll.config(command=self.serverList.yview)
    	self.serverList.bind('<Double-1>',self.getServerItemEvent)
    	self.serverList.grid(row=4,column=1,sticky=W)
    
	# let the user go back one folder 	
        self.clientBackBtn = Button(self)
        self.clientBackBtn["text"] = "Back"
        self.clientBackBtn["command"] = self.clientBackDir
        self.clientBackBtn.grid(row=5,sticky=W)
	

	## 
        self.uploadBtn = Button(self)
        self.uploadBtn["text"] = "Upload"
        self.uploadBtn["fg"]   = "red"
        self.uploadBtn["command"] =  self.uploadFile
        self.uploadBtn.grid(row=5, column=0)

        #  allow the user to make a file or folder
	self.clientMakeDirBtn = Button(self)
	self.clientMakeDirBtn["text"] = "Make Dir"
	self.clientMakeDirBtn["command"] = self.clientMakeDirButton
	self.clientMakeDirBtn.grid(row=5, sticky=E)

        # go back one folder on the server
	self.serverBackBtn = Button(self)
	self.serverBackBtn["text"] = "Back"
	self.serverBackBtn["command"] = self.serverBackDir
	self.serverBackBtn.grid(row=5,column=1,sticky=W)
	
	##
        self.downloadBtn = Button(self)
        self.downloadBtn["text"] = "Download"
        self.downloadBtn["command"] = self.downloadFile
        self.downloadBtn.grid(row=5,column=1, sticky=S)

	##
        self.serverMakeDirBtn = Button(self)
	self.serverMakeDirBtn["text"] = "Make Dir"
	self.serverMakeDirBtn["command"] = self.serverMakeDirButton
	self.serverMakeDirBtn.grid(row=5,column=1, sticky=E)
		
    def __init__(self, master=None):
        Frame.__init__(self, master)
        fileviewer.unrestrictFilespace()
        self.grid()
        self.createWidgets()
	self.repaint()
        

root = Tk()
root.title("fileRover")
root.resizable(0,0)
app = Application(master=root)
app.mainloop()

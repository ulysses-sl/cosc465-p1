#!/usr/bin/env python3

__author__ = "jsommers@colgate.edu"
__doc__ = '''
A simple model-view controller-based message board/chat client application.
'''
import sys
if sys.version_info[0] != 3:
    print ("This code must be run with a python3 interpreter!")
    sys.exit()

import tkinter
import socket
from select import select
import argparse

class MessageBoardNetwork(object):
    '''
    Model class in the MVC pattern.  This class handles
    the low-level network interactions with the server.
    It should make GET requests and POST requests (via the
    respective methods, below) and return the message or
    response data back to the MessageBoardController class.
    '''
    def __init__(self, host, port, retries, timeout):
        '''
        Constructor.  You should create a new socket
        here and do any other initialization.
        '''
        self.address = (host, port)
        self.socket = socket.socket(type=socket.SOCK_DGRAM)
        self.retries = retries
        self.timeout = timeout
        self.get = "GET"
        self.post = "POST {}::{}"
        self.seq = b'0'

    def nextSeq(self):
        if self.seq == b'0':
            self.seq = b'1'
        else:
            self.seq = b'0'

    def generateHeader(self, databytes):
        seq = self.seq
        checksum = 0
        for b in databytes:
            checksum ^= b
        return b'C' + seq + bytes([checksum])

    def generateRequest(self, data):
        databytes = data.encode()
        header = self.generateHeader(databytes)
        return header + databytes

    def sendRequest(self, request):
        """DRY!"""
        for t in range(self.retries):
            self.socket.sendto(request, self.address)
            availableSocket = select([self.socket], [], [], self.timeout)[0]
            if availableSocket:
                s = availableSocket[0]
                msg = s.recvfrom(1400)[0].decode()
                if msg[1] == self.seq.decode():
                    self.nextSeq()
                    return msg[3:]
        return "ERROR server does not respond"

    def getMessages(self):
        '''
        You should make calls to get messages from the message 
        board server here.
        '''
        data = self.get
        request = self.generateRequest(data)
        return self.sendRequest(request)

    def postMessage(self, user, message):
        '''
        You should make calls to post messages to the message 
        board server here.
        '''
        data = self.post.format(user, message)
        request = self.generateRequest(data)
        return self.sendRequest(request)


class MessageBoardController(object):
    '''
    Controller class in MVC pattern that coordinates
    actions in the GUI with sending/retrieving information
    to/from the server via the MessageBoardNetwork class.
    '''

    def __init__(self, myname, host, port, retries, timeout):
        self.name = myname
        self.view = MessageBoardView(myname)
        self.view.setMessageCallback(self.post_message_callback)
        self.net = MessageBoardNetwork(host, port, retries, timeout)

    def run(self):
        self.view.after(1000, self.retrieve_messages)
        self.view.mainloop()

    def post_message_callback(self, m):
        '''
        This method gets called in response to a user typing in
        a message to send from the GUI.  It should dispatch
        the message to the MessageBoardNetwork class via the
        postMessage method.
        '''
        result = self.net.postMessage(self.name, m)
        if result.startswith("OK"):
            # sometimes, right after server is unresponsive,
            # the server would send the entire message list
            # instead of simple OK sign.
            self.view.setStatus("Message Sent")
        else:
            self.view.setStatus(result)

    def split_messages(self, raw_data):
        m = raw_data[3:].split("::")
        messages = []
        for i in range(0, len(m), 3):
            messages.append(" ".join(m[i:i+3]))
        return messages

    def retrieve_messages(self):
        '''
        This method gets called every second for retrieving
        messages from the server.  It calls the MessageBoardNetwork
        method getMessages() to do the "hard" work of retrieving
        the messages from the server, then it should call 
        methods in MessageBoardView to display them in the GUI.

        You'll need to parse the response data from the server
        and figure out what should be displayed.

        Two relevant methods are (1) self.view.setListItems, which
        takes a list of strings as input, and displays that 
        list of strings in the GUI, and (2) self.view.setStatus,
        which can be used to display any useful status information
        at the bottom of the GUI.
        '''
        self.view.after(1000, self.retrieve_messages)
        messagedata = self.net.getMessages()
        print(messagedata)
        if messagedata.startswith("OK"):
            messages = self.split_messages(messagedata)
            self.view.setListItems(messages)
            status = "{} messages retrieved".format(len(messages))
            self.view.setStatus(status)
        else:
            self.view.setStatus(messagedata)


class MessageBoardView(tkinter.Frame):
    '''
    The main graphical frame that wraps up the chat app view.
    This class is completely written for you --- you do not
    need to modify the below code.
    '''
    def __init__(self, name):
        self.root = tkinter.Tk()
        tkinter.Frame.__init__(self, self.root)
        self.root.title('{} @ messenger465'.format(name))
        self.width = 80
        self.max_messages = 20
        self._createWidgets()
        self.pack()

    def _createWidgets(self):
        self.message_list = tkinter.Listbox(self, width=self.width, height=self.max_messages)
        self.message_list.pack(anchor="n")

        self.entrystatus = tkinter.Frame(self, width=self.width, height=2)
        self.entrystatus.pack(anchor="s")

        self.entry = tkinter.Entry(self.entrystatus, width=self.width)
        self.entry.grid(row=0, column=1)
        self.entry.bind('<KeyPress-Return>', self.newMessage)

        self.status = tkinter.Label(self.entrystatus, width=self.width, text="starting up")
        self.status.grid(row=1, column=1)

        self.quit = tkinter.Button(self.entrystatus, text="Quit", command=self.quit)
        self.quit.grid(row=1, column=0)


    def setMessageCallback(self, messagefn):
        '''
        Set up the callback function when a message is generated 
        from the GUI.
        '''
        self.message_callback = messagefn

    def setListItems(self, mlist):
        '''
        mlist is a list of messages (strings) to display in the
        window.  This method simply replaces the list currently
        drawn, with the given list.
        '''
        self.message_list.delete(0, self.message_list.size())
        self.message_list.insert(0, *mlist)
        
    def newMessage(self, evt):
        '''Called when user hits entry in message window.  Send message
        to controller, and clear out the entry'''
        message = self.entry.get()  
        if len(message):
            self.message_callback(message)
        self.entry.delete(0, len(self.entry.get()))

    def setStatus(self, message):
        '''Set the status message in the window'''
        self.status['text'] = message

    def end(self):
        '''Callback when window is being destroyed'''
        self.root.mainloop()
        try:
            self.root.destroy()
        except:
            pass

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='COSC465 Message Board Client')
    parser.add_argument('--host', dest='host', type=str, default='localhost',
                        help='Set the host name for server to send requests to (default: localhost)')
    parser.add_argument('--port', dest='port', type=int, default=1111,
                        help='Set the port number for the server (default: 1111)')
    parser.add_argument("--retries", dest='retries', type=int, default=3,
                        help='Set the number of retransmissions in case of a timeout')
    parser.add_argument("--timeout", dest='timeout', type=float, default=0.1,
                        help='Set the RTO value')
    args = parser.parse_args()

    myname = input("What is your user name (max 8 characters)? ")

    app = MessageBoardController(myname, args.host, args.port, args.retries, args.timeout)
    app.run()


import sys
import time
import threading
from select import select
import os
from socket import *

host = '127.0.0.1'

class Peer:
    def __init__ (self, peerID, pingInterval):
        self.peerID = int(peerID)
        self.portNum = 12000 + int(peerID)

        self.firstsuccessor = None
        self.secondsuccessor = None
        self.firstpredecessor = None
        self.secondpredecessor = None

        self.pingInterval = int(pingInterval)

        # Indicates the last time its successor send a response
        self.lastPingFirst = 0
        self.lastPingSecond = 0

        # List of file number that is stored
        self.filedata = []

        threading.Thread(target=self.TCPserver, daemon=True).start()
        
    # Used to set its first and second successor
    # Then it will start the ping server and begin pinging other peers
    def begin(self, firstsuccessor, secondsuccessor):
        self.firstsuccessor = int(firstsuccessor)
        self.secondsuccessor = int(secondsuccessor)
        threading.Thread(target=self.pingServer, daemon=True).start()
        threading.Thread(target=self.pingPeer, daemon=True).start()

    # Used when this peer is trying to join a network
    # It will send a join request to the known peer
    def beginJoin(self, knownPeer):
        self.sendHandler(knownPeer, f'join {self.peerID} {knownPeer}')

    # Used when this peer is trying to send TCP request to another peer
    # Also used if another peer is trying to tell this peer to change successor
    def sendHandler(self, peerID, data):
        client = socket(AF_INET, SOCK_STREAM)
        client.connect((host, 12000 + int(peerID)))
        client.sendall(data.encode())

        msglst = client.recv(1024)
        
        # If msg is 'skip' do nothing
        # If msg is 'update' update its first and second successor
        # If msg is 'abrupt' this means that a peer has done abrupt quitting. Update successors.
        msg = msglst.decode().split(' ')
        
        if msg[0] == 'skip':
            pass

        elif msg[0] == 'update':
            self.secondsuccessor = int(msg[1])

            print(f'> Successor Change request received')
            print(f'> My new first successor is Peer {self.firstsuccessor}.')
            print(f'> My new second successor is Peer {self.secondsuccessor}.')

        elif msg[0] == 'abrupt':
            if msg[1] != 'nope':
                self.firstsuccessor = int(msg[1])

            self.secondsuccessor = int(msg[2])

            print(f'> My new first successor is Peer {self.firstsuccessor}')
            print(f'> My new second successor is Peer {self.secondsuccessor}')

        client.close()

    # Starts the TCP server
    def TCPserver(self):
        server = socket(AF_INET, SOCK_STREAM)
        server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        server.bind((host,  self.portNum))
        server.listen(5)
        
        while True:
            client, addr = server.accept()

            threading.Thread(target=self.recvHandler, args=(client, addr), daemon=True).start()

    # Main receiver handler
    # Will receive a request from the client then run according to the request.
    def recvHandler(self, client, addr):
            data = client.recv(1024)
            msg = data.decode().split(' ')

            # A peer is trying to join (join <new peer> <sender>)
            # Result is 1 when the join request is forwarded to next peer and the predecessor will do nothing.
            # Result is 0 when join request is accepted and new peer will become the first successor. The predecessor will be sent an update msg to update its second successor.
            # msg format = 'join <sender_id > <known_id>'
            if msg[0] == 'join':
                # result returns 0 if new peer successfully joins.
                # result returns 1 if the join message is sent to next successor.
                result = self.join(int(msg[1]))
                
                # If <sender_id> and <known_id> is the same do nothing
                # Else send 'update' code to let sender know it can run.
                if result == 0:
                    if int(msg[1]) == int(msg[2]):
                        client.sendall(f'skip'.encode())
                    else:
                        client.sendall(f'update {msg[1]}'.encode())
                if result == 1:
                    client.sendall(f'skip'.encode())

            # Successful in joining. 
            # First successor will be its predecessor first successor and second successor will be its predecessor second successor.
            # First predecessor will be the sender and second predecessor will be the sender's first predecessor.
            # msg format = 'ok <first successor> <second_successor> <first_predecessor> <second_predecessor>'
            if msg[0] == 'ok':
                self.begin(msg[1], msg[2])
                self.firstpredecessor = msg[3]
                self.secondpredecessor = msg[4]
                client.sendall('skip'.encode())

                print(f'> Join request has been accepted')
                print(f'> My first successor is Peer {self.firstsuccessor}')
                print(f'> My second successor is Peer {self.secondsuccessor}')

            # Indicating that a peer has gracefully exited the network
            # If code (msg[1]) is 1, it means that this peer is its first predecessor
            # if code (msg[1]) is 2, it means that this peer is its second predecessor
            # msg format = 'exit <code> <exiting_peer> <new_first_successor> <new_second_successor>'
            if msg[0] == 'exit':
                if msg[1] == '1':
                    #first pred
                    self.firstsuccessor = int(msg[3])
                    self.secondsuccessor = int(msg[4])

                    print(f'> Peer {msg[2]} will depart from the network.')
                    print(f'> My new first successor is Peer {self.firstsuccessor}')
                    print(f'> My new second successor is Peer {self.secondsuccessor}')

                if msg[1] == '2':
                    #2nd pred
                    self.secondsuccessor = int(msg[3])
                    print(f'> Peer {msg[2]} will depart from the network.')
                    print(f'> My new first successor is Peer {self.firstsuccessor}')
                    print(f'> My new second successor is Peer {self.secondsuccessor}')
                    
            # Indicating that there is a peer that has done the abrupt quitting
            # If code (msg[1]) is 1, it means that this peer is its first successor
            # If code (msg[1]) is 2, it means that this peer is its second successor
            # msg format = 'abrupt <code>'
            if msg[0] == 'abrupt':
                if msg[1] == '1':
                    #first suc
                    client.sendall(f'abrupt {self.peerID} {self.firstsuccessor}'.encode())

                if msg[1] == '2':
                    #2nd suc
                    client.sendall(f'abrupt nope {self.firstsuccessor}'.encode())

            # Indicating a store request
            # msg format = 'store <filenumber>'
            if msg[0] == 'store':
                self.store(int(msg[1]))
                client.sendall('skip'.encode())
            
            # Indicating a request file request
            # msg format = 'request <filenumber> <requestor_id>'
            # At first, <requestor_id> will be None
            if msg[0] == 'request':
                self.request(int(msg[1]), int(msg[2]))
                client.sendall('skip'.encode())

            # Indicating that this peer is receving a file
            # msg format 'sending <client> <addr> <filenumber> <sender_id>'
            if msg[0] == 'sending':
                self.receive(client, addr, int(msg[1]), int(msg[2]))

            client.close()

    # Join function
    # Check if peer is eligible to join as next successor
    def join(self, msg):
        # If newpeer_id is in between of this peer id and this peer's sucessor, new peer will join as this peer's new first successor.
        # Else it will forward the join request to its successor.
        if msg > self.peerID and msg < self.firstsuccessor:
            # Sends an 'ok' message to new peer to indicate that new peer succesfully joins the network and will become this peer's first successor.
            # It also sends the new peer first and second successor
            self.sendHandler(msg, f'ok {self.firstsuccessor} {self.secondsuccessor} {self.firstpredecessor} {self.secondpredecessor}')
            self.secondsuccessor = self.firstsuccessor
            self.firstsuccessor = msg

            print(f'> Peer {msg} Join request received.')
            print(f'> My new first successor is Peer {self.firstsuccessor}.')
            print(f'> My new second successor is Peer {self.secondsuccessor}.')

            return 0
        else:
            print(f'> Peer {msg} Join request forward to my successor.')
            self.sendHandler(self.firstsuccessor, f'join {msg} {self.peerID}')
            return 1

    # UDP server for ping requests
    def pingServer(self):
        UDPserver = socket(AF_INET, SOCK_DGRAM)
        UDPserver.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        UDPserver.bind((host, self.portNum))
        
        # It will receive ping requests from predecessor
        # msg format = '<sender_id> <sender's first successor> <sender's second successor>'
        while True:
            data, addr = UDPserver.recvfrom(1024)
            msg = data.decode('utf-8').split(' ')
                
            print(f'Ping request message received from Peer {msg[0]}')

            # If this peer is the sender's first successor, this peer will store the sender id as its first predecessor
            # If this peer is the sender's second successor, this peer will store the sender id as its second predecessor
            if int(self.peerID) == int(msg[1]):
                self.firstpredecessor = int(msg[0])
            elif int(self.peerID) == int(msg[2]):
                self.secondpredecessor = int(msg[0])
            
            # Set this peer's predecessor if the predecessors are None
            if self.firstpredecessor == None:
                self.firstpredecessor = int(msg[0])
            elif self.secondpredecessor == None:
                self.secondpredecessor = int(msg[0])

            # Send response
            UDPserver.sendto(f'{self.peerID}'.encode(), addr)
    
    # Used to ping successors
    def pingPeer(self):
        s1 = socket(AF_INET, SOCK_DGRAM)
        s1.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        s2 = socket(AF_INET, SOCK_DGRAM)
        s2.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        
        while True:
            now = time.time()
            # Send msg to successors
            # msg format = <self id> <successor1> <successor2>
            s1.sendto(f'{self.peerID} {self.firstsuccessor} {self.secondsuccessor}'.encode(), (host, 12000 + self.firstsuccessor)) 
            s2.sendto(f'{self.peerID} {self.firstsuccessor} {self.secondsuccessor}'.encode(), (host, 12000 + self.secondsuccessor))

            print(f'Ping requests were sent to Peer {self.firstsuccessor} and {self.secondsuccessor}')

            s1.settimeout(1.0)
            s2.settimeout(1.0)

            # If response is received from successors, it will reset the lastPing timers to indicate the last time the successors send response.
            try:
                msg, addr = s1.recvfrom(1024)
                decoded = msg.decode('utf-8')
                print(f'Ping response received from Peer {decoded}')
                self.lastPingFirst = time.time()
            except:
                pass
            
            try:
                msg, addr = s2.recvfrom(1024)
                decoded = msg.decode('utf-8')
                print(f'Ping response received from Peer {decoded}')
                self.lastPingSecond = time.time()
            except:
                pass

            # If it is more than 45 since this peer receive a response from a successor, it will indicate that the successor has done abrupt quit. 
            # Sends abrupt msg to second successor with code 1 which means that this peer's first successor is gone or code 2 which means that this peer's second successor is gone.
            if now - self.lastPingFirst > 45 and self.lastPingFirst != 0:
                print(f'> Peer {self.firstsuccessor} is no longer alive.')
                self.sendHandler(self.secondsuccessor, f'abrupt 1 {self.peerID}')

            if now - self.lastPingSecond > 45 and self.lastPingSecond != 0:    
                print(f'> Peer {self.secondsuccessor} is no longer alive.')
                self.sendHandler(self.firstsuccessor, f'abrupt 2 {self.peerID}')

            # Wait according to ping interval
            time.sleep(self.pingInterval)

    # Quit gracefully
    def quit(self):
        # Notify predecessors
        # msg format = exit <code> <self id> <firstsuccessor> <secondsuccessor>
        if self.firstpredecessor != None:
            self.sendHandler(self.firstpredecessor, f'exit 1 {self.peerID} {self.firstsuccessor} {self.secondsuccessor}')
        if self.secondpredecessor != None:
            self.sendHandler(self.secondpredecessor, f'exit 2 {self.peerID} {self.firstsuccessor} {self.secondsuccessor}')

    # Store file
    def store(self, filenum):
        # Check hash
        hash = filenum % 256

        # Conditions that allow a peer to store a filenumber
        store = 0
        cond1 = int(self.peerID) == hash
        cond2 = hash < int(self.peerID) and hash > int(self.firstpredecessor)
        cond3 = int(self.peerID) < int(self.firstpredecessor) and hash > int(self.firstpredecessor)
        cond4 = int(self.peerID) < int(self.firstpredecessor) and hash < int(self.peerID)

        # If a condition is met, it will store the filenumber
        # Else it will forward the request to its first successor.
        if cond1 or cond2 or cond3 or cond4:
            store = 1
            pass
        else:
            print(f'> Store {filenum:04} request forwarded to my successor.')
            self.sendHandler(self.firstsuccessor, f'store {filenum}')

        # Store filenumber if it does not exist yet in its filedata list
        if store == 1:
            print(f'> Store {filenum:04} request accepted.')
            if int(filenum) not in self.filedata:
                self.filedata.append(int(filenum))

    # Request file
    def request(self, filenum, id = None):
        # First peer that requests data will immediately forward the request to successor
        if id == None:
            print(f'> File request for {filenum:04} has been sent to my successor.')
            self.sendHandler(self.firstsuccessor, f'request {int(filenum)} {int(self.peerID)}')
            return
        # If the request returns back to requestor, it will wait until a peer stores the file.
        if id == self.peerID:
            print(f'> File request for {filenum:04} is not found.')
            return

        hash = filenum % 256
        # Conditions that allow a peer to send a file
        cond1 = int(self.peerID) == hash
        cond2 = hash < int(self.peerID) and hash > int(self.firstpredecessor)
        cond3 = int(self.peerID) < int(self.firstpredecessor) and hash > int(self.firstpredecessor)
        cond4 = int(self.peerID) < int(self.firstpredecessor) and hash < int(self.peerID)

        # If all conditions are fulfilled it will start sending file
        # Else it will forward request to next successor
        if cond1 or cond2 or cond3 or cond4:
            if filenum not in self.filedata:
                print(f'> File {filenum:04} does not exist.')
            else:
                print(f'> File {filenum:04} is stored here.')
                self.send(int(filenum), int(id))
        else:
            print(f'> Request for File {filenum:04} has been received, but the file is not stored here.')
            self.sendHandler(self.firstsuccessor, f'request {int(filenum)} {int(id)}')

    # Used to send file
    def send(self, filenum, id):
        client = socket(AF_INET, SOCK_STREAM)
        client.connect((host, 12000 + int(id)))

        # Send a 'sending' request to requestor to indicate that this peer is sending file.
        client.sendall(f'sending {filenum} {self.peerID}'.encode())
        
        # Start sending file after receiving 'continue' request
        data = client.recv(1024)
        msg = data.decode()
        if msg == 'continue':
            # Try to open file, if it does not exist, it will not send back anything
            # If successful, it will start sending file.
            try: 
                f = open (format(filenum, '04') + '.pdf', 'rb')
                print(f'> Sending file {filenum:04} to Peer {id}.')
                data = f.read()
                while (data):
                    client.sendall(data)
                    data = f.read()
                print(f'> The file has been sent.')
                f.close()
            except:
                print(f'> File {filenum:04} does not exist.')

        client.close()

    # Used to receive file
    def receive(self, client, addr, filenum, id):
        # Opens new file and send a 'continue' request to let sender know that it may continue
        f = open('received_' + format(filenum, '04') + '.pdf', 'wb')
        client.sendall('continue'.encode())
        
        print(f'> Peer {id} had File {filenum:04}.')

        client.settimeout(1.0)

        try:
        # If does not receive any message, it means file does not exist
            data = client.recv(1024)
            # If successful, it will start receiving file
            print(f'> Receiving File {filenum:04} from Peer {id}.')
            while (data):
                f.write(data)
                data = client.recv(1024)
            print(f'> File {filenum:04} received.')
            f.close()
        except:
            print(f'> File {filenum:04} does not exist.')
            return



# If peer is initialising
if sys.argv[1] == 'init':
    p = Peer(sys.argv[2], sys.argv[5])
    p.begin(sys.argv[3], sys.argv[4])

# If peer is trying to join a network
if sys.argv[1] == 'join':
    p = Peer(sys.argv[2], sys.argv[4])
    p.beginJoin(sys.argv[3])

# Main input
print('\nType quit to exit\n')
while True:
    userinput = input()
    command = userinput.split(' ')

    if command[0].lower() == 'quit':
        p.quit()
        sys.exit()

    elif command[0].lower() == 'store':
        if len(command) != 2 or command[1].isdigit == False or len(command[1]) != 4:
            print('Argument error (store <4-digit filename>)')
        else:
            p.store(int(command[1]))

    elif command[0].lower() == 'request':
        if len(command) != 2 or command[1].isdigit == False or len(command[1]) != 4:
            print('Argument error (request <4-digit filename>)')
        else:
            p.request(int(command[1]))
    else:
        print('Invalid command.')
# p2p
Peer-to-Peer Network using Distributed Hash Table.

This program is called p2p.py and it is used to create a peer in order to establish a peer-to-peer 
DHT network.
p2p.py contains the class Peer and the main thread. The main thread is located at the end of 
the program. Peer class contains all the functions that each peer requires, TCP server as well as 
the UDP server.

## TCP server(def TCPserver( ) and recvHandler( ) )
Each peer has its own TCP server that is set up during its initial initialization. The TCP server will 
be online and ready to receive any request until the peer quits. Each peer’s TCP port number 
will be 12000 + its id.
All incoming TCP request will go through the TCP server and it will respond according to the 
code since all incoming TCP request will have a code as its first argument (e.g. 'join <sender_id > 
<known_id>' -> code is join).

## UDP server(def pingServer( ) )
Each peer has its own UDP server for pinging. The UDP server will start running after knowing 
its first and second successor. Each peer’s UDP port number will be 12000 + its id.
All incoming ping request will go through the UDP server. After receiving ping request from its 
predecessors, it will reply with a response to the predecessors.

## Ping peer(def pingPeer ( ) )
Each peer has 2 UDP socket to send its ping request to their successors. After sending the ping 
request, it will wait until it receives a response. 
If the response is not received until a certain period, it shows that the successor is no longer 
alive, and it will change its successor. It will also send a TCP message to one of its successors to 
indicate that one of their successors is no longer alive.

## Sending TCP requests(def sendHandler( ) )
Whenever a peer needs to send a TCP request to another peer, it will open a socket and 
connect to the target then it will send the TCP request. Then it will receive a response from the 
target. 
Some response will have a ‘skip’ code which means that the peer does not need to do anything. 
However, there is some cases where the peer will need to update its own data such as when a 
peer is trying to join a network or when a peer has done abrupt quitting. When a peer receives 
the code ‘abrupt’ or ‘update’ it means that the peer needs to update its existing data.

## Join (def join ( ) )
A new peer sends a request to a known peer
If the peer id is between the known peer’s id and its successor, it will join the network. Else the 
known peer will send a request to its successor to inform that a new peer is trying to join the 
network. This step will repeat until it successfully find a spot where the id is in between 2 peer.

## Quit (def quit( ) )
There are 2 cases of quitting: graceful quit and abrupt quit.
1. In the case of graceful quitting, the peer will send a TCP message to its predecessors to 
indicate that it is quitting. This will allow the predecessors to update their successors 
accordingly
2. In the case of abrupt quitting, its predecessors will receive no response until the set 
time limit. When it reaches the time limit, its predecessors will automatically update its 
successors accordingly.
The first predecessor will send a TCP request to the its second successor to know its new 
successors. The second predecessor will send a TCP request to its first successor to 
know its new successors.

## Store (def store( ) )
When a peer received a store command, it will first check if it is appropriate to store the file. If 
not, it will send a store request to the next successor. This will repeat until the appropriate 
place is found.

## Retrieval (def receive( ) and def send( ) )
When a peer received a request command, it will send a data retrieval request to its successor 
to check where the file is stored. This will repeat until the file is found. After the file is found, 
the peer will establish a connection to the target and start receiving the file.

## DHT
The DHT identity of a peer is drawn from the range [0,255]. 
Filenames are four-digit numbers such as 0000, 0159, 1890, etc. 
Hash function used to produce the key is given as modulus(filename/256), which results in a key space of [0,255] matching the DHT identity space. For example, the hash of file 2067 is 19.
A file producing a hash of n is stored in the peer that is the closest successor of n in the
circular DHT.


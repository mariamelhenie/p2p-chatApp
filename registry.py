from socket import *
import threading
import select
import logging
import db

# This class is used to process the peer messages sent to registry
# for each peer connected to registry, a new client thread is created
class ClientThread(threading.Thread):
    # initializations for client thread
    def __init__(self, ip, port, tcpClientSocket):
        threading.Thread.__init__(self)
        # ip of the connected peer
        self.ip = ip
        # port number of the connected peer
        self.port = port
        # socket of the peer
        self.tcpClientSocket = tcpClientSocket
        # username, online status and udp server initializations
        self.username = None
        self.isOnline = True
        self.udpServer = None
        print("New thread started for " + ip + ":" + str(port))

    # main of the thread
    def run(self):
        # locks for thread which will be used for thread synchronization
        self.lock = threading.Lock()
        print("Connection from: " + self.ip + ":" + str(port))
        print("IP Connected: " + self.ip)
        # message[1]=username , message[2]=password
        while True:
            try:
                # waits for incoming messages from peers
                message = self.tcpClientSocket.recv(1024).decode().split()
                logging.info("Received from " + self.ip + ":" + str(self.port) + " -> " + " ".join(message))
                # message[1]=username, message[2]=password

                #   JOIN    #
                if message[0] == "JOIN":
                    # join-exist is sent to peer,
                    # if an account with this username already exists
                    if db.is_account_exist(message[1]):
                        response = "join-exist"
                        print("From-> " + self.ip + ":" + str(self.port) + " " + response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())

                    # join-success is sent to peer,
                    # if an account with this username != exist, and the account is created
                    else:
                        db.register(message[1], message[2])
                        response = "join-success"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())



                #   LOGIN    #
                elif message[0] == "LOGIN":
                    # login-account-not-exist is sent to peer,
                    # if an account with the username does not exist
                    if not db.is_account_exist(message[1]):
                        response = "login-account-not-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())

                    # login-online is sent to peer,
                    # if an account with the username already online
                    elif db.is_account_online(message[1]):
                        response = "login-online"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())
                    # login-success is sent to peer,
                    # if an account with the username exists and not online
                    else:
                        # retrieves the account's password, and checks if the one entered by the user is correct
                        retrievedPass = db.get_password(message[1])
                        # if password is correct, then peer's thread is added to threads list
                        # peer is added to db with its username, port number, and ip address
                        if retrievedPass == message[2]:
                            self.username = message[1]
                            self.lock.acquire()
                            try:
                                tcpThreads[self.username] = self
                            finally:
                                self.lock.release()

                            db.user_login(message[1], self.ip, message[3])
                            # login-success is sent to peer,
                            # and a udp server thread is created for this peer, and thread is started
                            # timer thread of the udp server is started
                            response = "login-success"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                            self.udpServer = UDPServer(self.username, self.tcpClientSocket)
                            self.udpServer.start()
                            self.udpServer.timer.start()
                            chatroom_name = message[4]
                        # if password not matches and then login-wrong-password response is sent
                        else:
                            response = "login-wrong-password"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())

                #   LOGOUT  #
                elif message[0] == "LOGOUT":
                    # if user is online,
                    # removes the user from onlinePeers list
                    # and removes the thread for this user from tcpThreads
                    # socket is closed and timer thread of the udp for this
                    # user is cancelled
                    if len(message) > 1 and message[1] != None and db.is_account_online(message[1]):
                        db.user_logout(message[1])
                        self.lock.acquire()
                        try:
                            if message[1] in tcpThreads:
                                del tcpThreads[message[1]]
                        finally:
                            self.lock.release()
                        print(self.ip + ":" + str(self.port) + " is logged out")
                        self.tcpClientSocket.close()
                        self.udpServer.timer.cancel()
                        chatroom_name = message[4]
                        break
                    else:
                        self.tcpClientSocket.close()
                        break

                #   SEARCH  #
                elif message[0] == "SEARCH":
                    # checks if an account with the username exists
                    if db.is_account_exist(message[1]):
                        # checks if the account is online
                        # and sends the related response to peer
                        if db.is_account_online(message[1]):
                            peer_info = db.get_peer_ip_port(message[1])
                            response = "search-success " + peer_info[0] + ":" + peer_info[1]
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                        else:
                            response = "search-user-not-online"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                    # enters if username does not exist
                    else:
                        response = "search-user-not-found"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())

                elif message[0] == "ONLINE":
                    response = list(tcpThreads.keys())
                    self.tcpClientSocket.send(str(response).encode())

                # CHATROOM
                elif message[0] == "CREATE_ROOM":
                    # Extract chatroom name from the message
                    chatroom_name = message[1]
                    RoomCreator=message[2]
                    # chatroom-not-exist is sent to peer if the chatroom name does not exist
                    if not db.is_chatroom_exist(chatroom_name):
                        db.create_room(chatroom_name,RoomCreator)  # Add the chatroom
                        response = "create-room-success"
                        logging.info(f"Send to {self.ip}:{str(self.port)} -> {response}")
                        self.tcpClientSocket.send(response.encode())

                    else:
                        response = "Room exist"
                        print("From-> " + self.ip + ":" + str(self.port) + " " + response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())


             #if user is already in the room must be added
                elif message[0] == "JOIN_ROOM":
                    chatroom_name = message[1]
                    if db.is_chatroom_exist(chatroom_name):
                        db.join_chat_room(chatroom_name,message[2])
                        response = "join-room-success"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response))
                        self.tcpClientSocket.send(response.encode())
                    else:
                        response = "join-room-failure"
                        print("From-> " + self.ip + ":" + str(self.port) + " " + response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                        self.tcpClientSocket.send(response.encode())

                elif message[0] == "get_users":
                    room_details = db.get_users(message[1])
                    response = "onlineusers"
                    for user in room_details:
                        response += ":" + user

                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response))


                    self.tcpClientSocket.send(response.encode())
                elif message[0] == "LEAVE_ROOM":
                        db.leave_Chatroom(message[1], message[2])
                        print(self.ip + ":" + str(self.port) + " is leaving chatroom")
                        response = message[2]+" " + "Left room " + message[1]
                        self.tcpClientSocket.send(response.encode())
                        self.tcpClientSocket.close()
                        self.udpServer.timer.cancel()
                        break
                else:
                    self.tcpClientSocket.close()
                    break
            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))

            except threading.ThreadError as te:
                logging.error(f"Thread error: {te}")

            except IndexError as ie:
                logging.error(f"Index error: {ie}")

            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}")

            except Exception as e:
                logging.error(f"An unexpected error occurred in ClassroomChatThread: {e}")

    # function for resettin the timeout for the udp timer thread
    def resetTimeout(self):
        self.udpServer.resetTimer()


# implementation of the udp server thread for clients
class UDPServer(threading.Thread):
    # udp server thread initializations
    def __init__(self, username, clientSocket):
        threading.Thread.__init__(self)
        self.username = username
        # timer thread for the udp server is initialized
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.tcpClientSocket = clientSocket

    # if hello message != received before timeout
    # then peer is disconnected
    def waitHelloMessage(self):
        if self.username != None:
            db.user_logout(self.username)
            if self.username in tcpThreads:
                del tcpThreads[self.username]
        self.tcpClientSocket.close()
        print("Removed " + self.username + " from online peers")
        db.user_logout(self.username)

    # resets the timer for udp server
    def resetTimer(self):
        self.timer.cancel()
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.timer.start()




# tcp and udp server port initializations
print("Registy started...")
port = 15713
portUDP = 15713

# db initialization
db = db.DB()

# gets the ip address of this peer
# first checks to get it for windows devices
# if the device that runs this application != windows
# it checks to get it for macos devices
hostname = gethostname()
try:
    host = gethostbyname(hostname)
except gaierror:
    import netifaces as ni

    host = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']

print("Registry IP address: " + host)
print("Registry port number: " + str(port))

# onlinePeers list for online account
onlinePeers = {}
# accounts list for accounts
accounts = {}
# tcpThreads list for online client's thread
tcpThreads = {}
# chatroom list
chatrooms = {}

# tcp and udp socket initializations
tcpSocket = socket(AF_INET, SOCK_STREAM)
udpSocket = socket(AF_INET, SOCK_DGRAM)

try:
    tcpSocket.bind((host, port))
except OSError as oErr:
    logging.error(f"Error binding TCP socket: {oErr}")

try:
    udpSocket.bind((host, portUDP))
except OSError as oErr:
    logging.error(f"Error binding UDP socket: {oErr}")

tcpSocket.listen(5)

# input sockets that are listened
inputs = [tcpSocket, udpSocket]

# log file initialization
logging.basicConfig(filename="registry.log", level=logging.INFO)

while inputs:
    # monitors for the incoming connections
    readable, writable, exceptional = select.select(inputs, [], [])
    for s in readable:
        try:
            # if the message received comes to the tcp socket
            # the connection is accepted and a thread is created for it, and that thread is started
            if s == tcpSocket:
                tcpClientSocket, addr = tcpSocket.accept()
                newThread = ClientThread(addr[0], addr[1], tcpClientSocket)
                newThread.start()

            # if the message received comes to the udp socket
            elif s == udpSocket:
                # received the incoming udp message and parses it
                message, clientAddress = s.recvfrom(1024)
                message = message.decode().split()
                # checks if it is a hello message
                if message[0] == "HELLO":
                    # checks if the account that this hello message
                    # is sent from is online
                    if message[1] in tcpThreads:
                        # resets the timeout for that peer since the hello message is received
                        tcpThreads[message[1]].resetTimeout()
                        logging.info(
                            "Received from " + clientAddress[0] + ":" + str(clientAddress[1]) + " -> " + " ".join(
                                message))
        except OSError as se:
            logging.error(f"Socket error: {se}")

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

        except threading.ThreadError as te:
            logging.error(f"Thread error: {te}")

        except IndexError as ie:
            logging.error(f"Index error: {ie}")

# registry tcp socket is closed
tcpSocket.close()

# registry tcp socket is closed
tcpSocket.close()




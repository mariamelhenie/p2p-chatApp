from pymongo import MongoClient

class DB:
    # Constructor method
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['p2p-chat']

    # checks if an account with the username exists
    def is_account_exist(self, username):
        user_exists = self.db.accounts.find_one({'username': username})
        if user_exists is not None:
            return True
        else:
            return False

    def user_login(self, username, ip, port):
        online_peer = {
            "username": username,
            "ip": ip,
            "port": port
        }
        self.db.online_peers.insert_one(online_peer)

    def get_online_peers(self):
        online_peers_cursor = self.db.online_peers.find({})
        online_peers_list = []

        for peer in online_peers_cursor:
            online_peers_list.append(peer["username"])

        return online_peers_list


    # logs out the user
    def user_logout(self, username):
        self.db.online_peers.delete_one({"username": username})

    # retrieves the ip address and the port number of the username
    def get_peer_ip_port(self, username):
        res = self.db.online_peers.find_one({"username": username})
        return res["ip"], res["port"]

    def is_chatroom_exist(self, chatroomName):
        chatroom_exists = self.db.chatrooms.find_one({'chatroomName': chatroomName})
        if chatroom_exists is not None:
            return True
        else:
            return False


    # adds a chatroom to the database
    def create_room(self, chatroomName, creator_username):
        if not self.is_chatroom_exist(chatroomName):
            chatroom = {
                "chatroomName": chatroomName,
                "creator_username": creator_username,
                "peers": [creator_username]  # list of peers where beginning of list is hostname
            }
            self.db.accounts.update_one(
                {"username": creator_username}, {"$push": {"ChatRooms": chatroomName}}
            )
            self.db.chatrooms.insert_one(chatroom)



    def join_chat_room(self, chatroomName, username):  # add members to chatroom and update if new peer joined
        if not self.FindUserinChatroom(chatroomName,username):
            self.db.chatrooms.update_one(
                {"chatroomName": chatroomName}, {"$push": {"peers": username}}
            )
            self.db.accounts.update_one(
                {"username": username}, {"$push": {"ChatRooms": chatroomName}}
            )


    def FindUserinChatroom(self,chatroomName, username):
        return self.db.chatrooms.count_documents({'chatroomName': chatroomName, 'peers': username}) > 0

    def get_users(self, chatroomName):
        ChatRoom = self.db.chatrooms.find_one({"chatroomName": chatroomName})
        if ChatRoom and 'peers' in ChatRoom:
            # Return the list of users
            return ChatRoom['peers']

    def register(self, username, password):
        account = {
            "username": username,
            "password": password
        }
        self.db.accounts.insert_one(account)

    # retrieves the password for a given username
    def get_password(self, username):
        return self.db.accounts.find_one({"username": username})["password"]

    # checks if an account with the username online
    def is_account_online(self, username):
        if self.db.online_peers.count_documents({"username": username}) > 0:
            return True
        else:
            return False

    # logs in the user


    def leave_Chatroom(self, chatroomName, username):
        if self.FindUserinChatroom(chatroomName, username):
            # Remove the username from the chatroom's list of peers
            self.db.chatrooms.update_one(
                {"chatroomName": chatroomName},
                {"$pull": {"peers": username}}
            )
            

        
    def get_available_chat_rooms(self):
        # Retrieve all chatrooms from the database
        chat_rooms = self.db.chatrooms.find({}, {"chatroomName": 1, "_id": 0})

        # Extract the room names from the query result
        available_chat_rooms = [chat_room["chatroomName"] for chat_room in chat_rooms]

        # Return the list of available chat rooms
        return available_chat_rooms    














import paramiko
from paramiko import SSHClient

class rpi_conn():
 # connect to raspberry pi and run gesture recognition code. 

    def __init__(self, ip, port, user, password): 
        self.ip = ip 
        self.port = port 
        self.user = user 
        self.password = password
        self.connected = False
        self.username = ''
        self.roomcode = ''
        self.mode = ''
        self.parameters = ''
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    def connect(self):
        try:
            self.ssh.connect(self.ip, self.port, self.user, self.password)
        except:
            self.connected = False
            print("couldn\'t connect to Raspberry Pi, check connection information")
            return
        self.connected = True
        print("connected to Raspberry Pi")

    def set_conn_info(self, mode='', username='', roomcode=''):       
        if mode == 'm': 
            self.mode = ' -m \'m\''
        if username != '': 
            self.username = ' -u \'' + username + '\''
        if roomcode != '': 
            self.roomcode = ' -r \'' + roomcode + '\''

        self.parameters = self.mode + self.roomcode + self.username  

    def run(self):
        
        command = 'source berryconda3/bin/activate hitw; echo activated hitw conda env; cd Team1/GestureRecognition; python mqtt.py' + self.parameters 

        stdin,stdout,stderr=self.ssh.exec_command(command, get_pty=True)
        for line in iter(stdout.readline, ""):
            print(line, end="")

        print("command finished, closing SSH connection")
        self.ssh.close()

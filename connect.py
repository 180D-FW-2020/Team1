import paramiko
from paramiko import SSHClient

class rpi_conn():
    def __init__(self, ip, port, user, password): 
        self.ip = ip 
        self.port = port 
        self.user = user 
        self.password = password
        self.nickname = ''
        self.roomcode = ''
        self.mode = ''
        self.parameters = ''
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # try to connect to raspberry pi 
    def connect(self, raspi):
        try:
            self.ssh.connect(self.ip, self.port, self.user, self.password)
        except:
            raspi['success'] = False
            print("couldn\'t connect to Raspberry Pi, check connection information")
            return
        raspi['success'] = True
        print("connected to Raspberry Pi") 

    # set parameters for raspberry pi gesture recognition code 
    def set_conn_info(self, mode='', nickname='', roomcode=''):       
        if mode == 'm': 
            self.mode = ' -m \'m\''
        if nickname != '': 
            self.nickname = ' -n \'' + nickname + '\''
        if roomcode != '': 
            self.roomcode = ' -r \'' + roomcode + '\''

        self.parameters = self.mode + self.roomcode + self.nickname  

    # run gesture recognition code on raspberry pi 
    def run(self):
        command = 'source berryconda3/bin/activate hitw; echo activated hitw conda env; cd Team1/GestureRecognition; python mqtt.py' + self.parameters 

        stdin,stdout,stderr=self.ssh.exec_command(command, get_pty=True)
        for line in iter(stdout.readline, ""):
            print(line, end="")

        print("command finished, closing SSH connection")
        self.ssh.close()

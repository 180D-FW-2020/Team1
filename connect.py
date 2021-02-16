import paramiko
from paramiko import SSHClient

class rpi_conn():
 # Find all the directories you want to upload already in files.

    def connect(self, ip, port, user, password):
        self.connected = False
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(ip, port, user, password)
        except:
            self.connected = False
            return
        self.connected = True

    def run(self, mode='', username='', roomcode=''):
        self.username = ''
        self.roomcode = ''
        self.mode = ''
        if mode == 'm': 
            self.mode = ' -m \'m\''
        if username != '': 
            self.username = ' -u \'' + username + '\''
        if roomcode != '': 
            self.roomcode = ' -r \'' + roomcode + '\''

        self.parameters = self.mode + self.roomcode + self.username  
        
        command = 'source berryconda3/bin/activate hitw; echo activated hitw conda env; cd Team1/GestureRecognition; python mqtt.py' + self.parameters 

        stdin,stdout,stderr=self.ssh.exec_command(command, get_pty=True)
        for line in iter(stdout.readline, ""):
            print(line, end="")

        print("command finished, closing SSH connection")
        self.ssh.close()

import paramiko
from paramiko import SSHClient
import os

class rpi_conn():
 # Find all the directories you want to upload already in files.

    def set_conn_info(self, ip, port, user, pw):
        self.port=port
        self.ip=ip
        self.user=user
        self.pw=pw

    def connect(self):
        self.connected = False
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.ip, self.port, self.user, self.pw)
        except:
            self.connected = False
            return
        self.connected = True

    def run(self, mode='', username='', roomcode=''):
        self.remote_dir = '/home/pi/Team1/GestureRecognition'
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
        self.run_rpi = 'cd Team1/GestureRecognition && source activate hitw && python mqtt.py' + self.parameters

        stdin,stdout,stderr=self.ssh.exec_command(self.run_rpi, get_pty=True)
        for line in iter(stdout.readline, ""):
            print(line, end="")
        self.ssh.close()

#conda install -c anaconda paramiko

import os.path
import subprocess
from tkinter import *
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText


class Main:
    def __init__(self):
        # Persistent variables
        self.server_process = None
        self.log_content = ''
        self.previous_log_content = ''

        # Read latest log into previous log content
        if os.path.exists('testserver/logs/latest.log'):
            f = open('testserver/logs/latest.log')
            self.previous_log_content = f.read()

        # Create root frame / widget
        self.root = Tk()
        self.root.geometry("800x400")
        self.frame = Frame(self.root)
        self.frame.pack()

        # Banner menu
        self.banner_menu = Menu(self.frame)
        self.banner_menu.add_command(label="Project", command=self.changeProject)
        self.banner_menu.add_command(label="Version", command=self.changeVersion)
        self.root.config(menu=self.banner_menu)

        # Left and right division
        self.left_frame = Frame(self.root)
        self.left_frame.pack(side=LEFT)
        self.right_frame = Frame(self.root)
        self.right_frame.pack(side=RIGHT, fill=BOTH)

        # Buttons
        self.start_server = Button(self.left_frame, text="Start Server", command=self.startServer)
        self.start_server.pack(padx=3, pady=3)
        self.stop_server = Button(self.left_frame, text="Stop Server", command=self.stopServer)
        self.stop_server.pack(padx=3, pady=3)
        self.kill_server = Button(self.left_frame, text="Kill Server", command=self.killServer)
        self.kill_server.pack(padx=3, pady=3)

        # Console setup
        self.console_output = ScrolledText(self.right_frame)
        self.console_output.config(state=DISABLED)
        self.console_output.grid(row=0, column=0)
        self.console_entry = Entry(self.right_frame)
        self.console_entry.bind("<Return>", self.sendCommand)
        self.console_entry.grid(row=1, column=0, padx=3, pady=3)

        # Setup root window
        self.root.title("Test")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # Window functions
    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.killServer()
            self.root.destroy()

    # Widget functions
    def startServer(self):
        # Start server process
        self.server_process = subprocess.Popen('java -jar paper.jar --nogui', cwd="testserver/", stdin=subprocess.PIPE)

    def stopServer(self):
        if self.server_process is not None:
            self.server_process.stdin.write(bytes("stop" + '\r\n', 'ascii'))
            self.server_process.stdin.flush()
            self.server_process = None

    def killServer(self):
        if self.server_process is not None:
            self.server_process.kill()
            self.server_process = None

    def sendCommand(self, event):
        # Only send command and clear entry box if server is running
        if self.server_process is not None:
            command = self.console_entry.get()
            print("Command " + command)
            if command:
                self.server_process.stdin.write(bytes(command + '\r\n', 'ascii'))
                self.server_process.stdin.flush()
                self.console_entry.delete(0, 'end')

    def changeProject(self):
        pass

    def changeVersion(self):
        pass

    # GUI loop
    def customLoop(self):
        # Handle console input
        # command = input('')
        # if command:
        #     self.server_process.stdin.write(bytes(command + '\r\n', 'ascii'))
        #     self.server_process.stdin.flush()

        # Check if fully scrolled down before writing to console
        fully_scrolled_down = self.console_output.yview()[1] == 1.0

        # Update console
        if os.path.exists('testserver/logs/latest.log'):
            f = open('testserver/logs/latest.log')
            original_log = f.read()
            self.log_content = original_log
            self.log_content = self.log_content.replace(self.previous_log_content, '')
            if self.log_content != '':
                self.console_output.config(state=NORMAL)
                self.console_output.insert(INSERT, self.log_content)
                self.console_output.config(state=DISABLED)
            self.previous_log_content = original_log
            f.close()

        # Scroll console if it was already scrolled all the way down
        if fully_scrolled_down:
            self.console_output.see("end")

        # Recall loop
        self.root.after(100, self.customLoop)


main = Main()

# Start custom gui loop
main.customLoop()

main.root.mainloop()

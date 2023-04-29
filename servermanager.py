import os.path
import subprocess
from threading import Thread

import requests
from tkinter import *
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

# Static Variables
paper_versions: list = []
paper_builds: dict = {}


# Static Methods
def get_projects() -> list:
    if os.path.exists("TestServers"):
        return os.listdir("TestServers")
    else:
        return []


def get_project_versions(project) -> list:
    if os.path.exists("TestServers/" + project):
        return os.listdir("TestServers/" + project)
    else:
        return []


def get_paper_versions() -> list:
    global paper_versions
    if not paper_versions == []:
        return paper_versions
    r = requests.get("https://api.papermc.io/v2/projects/paper")
    if not r.status_code == 200:
        messagebox.showerror("Failed to get versions!", str(r.status_code) + ": " + r.reason)
        return []
    paper_versions = list(r.json()["versions"])
    paper_versions.reverse()
    return paper_versions


def get_paper_builds(version: str) -> list:
    global paper_builds
    if version in paper_builds.keys():
        return paper_builds[version]
    r = requests.get("https://api.papermc.io/v2/projects/paper/versions/" + version)
    if not r.status_code == 200:
        messagebox.showerror("Failed to get builds!", str(r.status_code) + ": " + r.reason)
        return []
    builds = list(r.json()["builds"])
    builds.reverse()
    paper_builds[version] = builds
    return builds


def console_reader(f, buffer):
    while True:
        line = f.readline()
        if line:
            buffer.append(line)
        else:
            break


class Main:
    # noinspection PyTypeChecker
    def __init__(self):
        # Persistent variables
        self.reader_thread: Thread = None
        self.console_buffer: list = []
        self.build_dropdown: OptionMenu = None
        self.version_dropdown: OptionMenu = None
        self.platform_dropdown: OptionMenu = None
        self.new_project_entry: Entry = None
        self.console_entry: Entry = None
        self.kill_server_button: Button = None
        self.stop_server_button: Button = None
        self.console_output: ScrolledText = None
        self.start_server_button: Entry = None
        self.right_frame: Frame = None
        self.left_frame: Frame = None
        self.banner_menu: Menu = None
        self.frame: Frame = None
        self.server_process = None
        self.log_content: str = ''
        self.previous_log_content: str = ''
        self.page: str = ''
        self.project: str = ''

        # Create root frame / widget
        self.root = Tk()
        self.root.geometry("800x400")

        # Setup root window
        self.root.title("Test")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Open page
        self.open_select_project_page()

    # Pages
    def clear_page(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def open_select_project_page(self):
        self.clear_page()
        self.page = "select"
        if len(get_projects()) == 0:
            self.open_new_project_page()
            return
        for project in get_projects():
            button = Button(self.root, text=project, command=lambda: self.select_project(project))
            button.pack()
        button = Button(self.root, text="Create New Project", command=self.open_project_page)
        button.pack()

    def open_new_project_page(self):
        self.clear_page()
        self.page = "new"
        label = Label(self.root, text="Enter a project name")
        label.pack(padx=5, pady=5)
        self.new_project_entry = Entry(self.root)
        self.new_project_entry.bind("<Return>", self.create_project)
        self.new_project_entry.pack()

    def open_select_version_page(self):
        self.clear_page()
        self.page = "version"
        if self.project == '':
            self.open_select_project_page()
            return
        # Left and right division
        self.left_frame = Frame(self.root)
        self.left_frame.pack(side=LEFT)
        self.right_frame = Frame(self.root)
        self.right_frame.pack(side=RIGHT)

        version_label = Label(self.left_frame, text="Choose a version")
        version_label.pack(side=TOP)
        new_label = Label(self.right_frame, text="Create a version")
        new_label.grid(row=0, column=0)
        self.platform_dropdown = OptionMenu(self.right_frame, StringVar(self.right_frame), "Paper", "Purpur", "Folia",
                                            command=self.select_platform)
        self.platform_dropdown.grid(row=1, column=0)
        self.version_dropdown = OptionMenu(self.right_frame, StringVar(self.right_frame), "")
        self.version_dropdown.grid(row=2, column=0)
        self.build_dropdown = OptionMenu(self.right_frame, StringVar(self.right_frame), "")
        self.version_dropdown.grid(row=3, column=0)

    def open_project_page(self):
        self.clear_page()
        self.page = "project"
        self.logging = False
        if self.project == '':
            self.open_new_project_page()
            return
        self.frame = Frame(self.root)
        self.frame.pack()

        # Banner menu
        self.banner_menu = Menu(self.frame)
        self.banner_menu.add_command(label="Change Project", command=self.open_select_project_page)
        self.banner_menu.add_command(label="Change Version", command=self.open_select_version_page)
        self.root.config(menu=self.banner_menu)

        # Left and right division
        self.left_frame = Frame(self.root)
        self.left_frame.pack(side=LEFT)
        self.right_frame = Frame(self.root)
        self.right_frame.pack(side=RIGHT, fill=BOTH)

        # Buttons
        self.start_server_button = Button(self.left_frame, text="Start Server", command=self.start_server)
        self.start_server_button.pack(padx=3, pady=3)
        self.stop_server_button = Button(self.left_frame, text="Stop Server", command=self.stop_server)
        self.stop_server_button.pack(padx=3, pady=3)
        self.kill_server_button = Button(self.left_frame, text="Kill Server", command=self.kill_server)
        self.kill_server_button.pack(padx=3, pady=3)

        # Console setup
        self.console_output = ScrolledText(self.right_frame)
        self.console_output.config(state=DISABLED)
        self.console_output.grid(row=0, column=0)
        self.console_entry = Entry(self.right_frame)
        self.console_entry.bind("<Return>", self.send_command)
        self.console_entry.grid(row=1, column=0, padx=3, pady=3)

        # Read latest log into previous log content
        if os.path.exists('TestServers/' + self.project + '/logs/latest.log'):
            f = open('TestServers/' + self.project + '/logs/latest.log')
            self.previous_log_content = f.read()

    # Project Creation
    def create_project(self, event):
        self.project = self.new_project_entry.get()
        if not os.path.exists("TestServers/" + self.project):
            os.makedirs("TestServers/" + self.project, exist_ok=True)
        self.open_project_page()

    def select_project(self, project):
        self.project = project
        self.open_project_page()

    def select_platform(self, selection):
        if selection == "Paper":
            self.version_dropdown.destroy()
            default = StringVar(self.right_frame)
            if not get_paper_versions() == []:
                default.set(get_paper_versions()[0])
            self.version_dropdown = OptionMenu(self.right_frame, default, *get_paper_versions(),
                                               command=self.select_version)
            self.version_dropdown.grid(row=2, column=0)

    def select_version(self, selection):
        self.build_dropdown.destroy()
        default = StringVar(self.right_frame)
        if not get_paper_builds(selection) == []:
            default.set(get_paper_builds(selection)[0])
        self.build_dropdown = OptionMenu(self.right_frame, default, *get_paper_builds(selection))
        self.build_dropdown.grid(row=3, column=0)

    # Window functions
    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.kill_server()
            self.root.destroy()

    # Widget functions
    def start_server(self):
        # Start server process
        self.server_process = subprocess.Popen('java -jar paper.jar --nogui', cwd="TestServers/" + self.project,
                                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.reader_thread = Thread(target=console_reader, args=(self.server_process.stdout, self.console_buffer))
        self.reader_thread.daemon = True
        self.reader_thread.start()

    def stop_server(self):
        if self.server_process is not None:
            self.server_process.stdin.write(bytes("stop" + '\r\n', 'ascii'))
            self.server_process = None

    def kill_server(self):
        if self.server_process is not None:
            self.server_process.kill()
            self.server_process = None

    def send_command(self, event):
        # Only send command and clear entry box if server is running
        if self.server_process is not None:
            command = self.console_entry.get()
            print("Command " + command)
            if command:
                self.server_process.stdin.write(bytes(command + '\r\n', 'ascii'))
                self.server_process.stdin.flush()
                self.console_entry.delete(0, 'end')

    # GUI loop
    def customLoop(self):
        if self.page == "project":
            # Check if fully scrolled down before writing to console
            fully_scrolled_down = self.console_output.yview()[1] == 1.0

            if self.console_buffer:
                self.console_output.config(state=NORMAL)
                self.console_output.insert(END, self.console_buffer.pop(0))
                self.console_output.config(state=DISABLED)

            # Scroll console if it was already scrolled all the way down
            if fully_scrolled_down:
                self.console_output.see("end")

        # Recall loop
        self.root.after(100, self.customLoop)


if __name__ == "__main__":
    main = Main()
    # Start custom gui loop
    main.customLoop()
    main.root.mainloop()

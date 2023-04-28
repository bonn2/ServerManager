import os.path
import subprocess
import requests
from tkinter import *
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

# Static Variables
paper_versions: list = []
paper_builds: dict = {}


# Static Methods
def getProjects():
    if os.path.exists("Test Servers"):
        return os.listdir("Test Servers")
    else:
        return []


def getProjectVersions(project):
    if os.path.exists("Test Servers/" + project):
        return os.listdir("Test Servers/" + project)
    else:
        return []


def getPaperVersions():
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


def getPaperBuilds(version: str):
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


class Main:
    # noinspection PyTypeChecker
    def __init__(self):
        # Persistent variables
        self.build_dropdown: OptionMenu = None
        self.version_dropdown: OptionMenu = None
        self.platform_dropdown: OptionMenu = None
        self.new_project_entry: Entry = None
        self.console_entry: Entry = None
        self.kill_server: Button = None
        self.stop_server: Button = None
        self.console_output: ScrolledText = None
        self.start_server: Entry = None
        self.right_frame: Frame = None
        self.left_frame: Frame = None
        self.banner_menu: Menu = None
        self.frame: Frame = None
        self.server_process = None
        self.log_content: str = ''
        self.previous_log_content: str = ''
        self.page: str = ''
        self.project: str = ''

        # Read latest log into previous log content
        if os.path.exists('testserver/logs/latest.log'):
            f = open('testserver/logs/latest.log')
            self.previous_log_content = f.read()

        # Create root frame / widget
        self.root = Tk()
        self.root.geometry("800x400")

        # Setup root window
        self.root.title("Test")
        self.root.protocol("WM_DELETE_WINDOW", self.onClosing)

        # Open page
        self.openSelectProjectPage()

    # Pages
    def clearPage(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def openSelectProjectPage(self):
        self.clearPage()
        self.page = "select"
        if len(getProjects()) == 0:
            self.openNewProjectPage()
            return
        for project in getProjects():
            button = Button(self.root, text=project, command=lambda: self.selectProject(project))
            button.pack()
        button = Button(self.root, text="Create New Project", command=self.openProjectPage)
        button.pack()

    def openNewProjectPage(self):
        self.clearPage()
        self.page = "new"
        label = Label(self.root, text="Enter a project name")
        label.pack(padx=5, pady=5)
        self.new_project_entry = Entry(self.root)
        self.new_project_entry.bind("<Return>", self.createProject)
        self.new_project_entry.pack()

    def openSelectVersionPage(self):
        self.clearPage()
        self.page = "version"
        if self.project == '':
            self.openSelectProjectPage()
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
                                            command=self.selectPlatform)
        self.platform_dropdown.grid(row=1, column=0)
        self.version_dropdown = OptionMenu(self.right_frame, StringVar(self.right_frame), "")
        self.version_dropdown.grid(row=2, column=0)
        self.build_dropdown = OptionMenu(self.right_frame, StringVar(self.right_frame), "")
        self.version_dropdown.grid(row=3, column=0)

    def openProjectPage(self):
        self.clearPage()
        self.page = "project"
        if self.project == '':
            self.openNewProjectPage()
            return
        self.frame = Frame(self.root)
        self.frame.pack()

        # Banner menu
        self.banner_menu = Menu(self.frame)
        self.banner_menu.add_command(label="Change Project", command=self.openSelectProjectPage)
        self.banner_menu.add_command(label="Change Version", command=self.openSelectVersionPage)
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

    # Project Creation
    def createProject(self, event):
        self.project = self.new_project_entry.get()
        if not os.path.exists("Test Servers/" + self.project):
            os.makedirs("Test Servers/" + self.project, exist_ok=True)
        self.openProjectPage()

    def selectProject(self, project):
        self.project = project
        self.openProjectPage()

    def selectPlatform(self, selection):
        if selection == "Paper":
            self.version_dropdown.destroy()
            default = StringVar(self.right_frame)
            if not getPaperVersions() == []:
                default.set(getPaperVersions()[0])
            self.version_dropdown = OptionMenu(self.right_frame, default, *getPaperVersions(),
                                               command=self.selectVersion)
            self.version_dropdown.grid(row=2, column=0)

    def selectVersion(self, selection):
        self.build_dropdown.destroy()
        default = StringVar(self.right_frame)
        if not getPaperBuilds(selection) == []:
            default.set(getPaperBuilds(selection)[0])
        self.build_dropdown = OptionMenu(self.right_frame, default, *getPaperBuilds(selection))
        self.build_dropdown.grid(row=3, column=0)

    # Window functions
    def onClosing(self):
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

    # GUI loop
    def customLoop(self):
        # Handle console input
        # command = input('')
        # if command:
        #     self.server_process.stdin.write(bytes(command + '\r\n', 'ascii'))
        #     self.server_process.stdin.flush()

        if self.page == "project":
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

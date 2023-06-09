import json
import os.path
import re
import shutil
import subprocess
import time
from threading import Thread
from tkinter import *
from tkinter import messagebox, filedialog
from tkinter.scrolledtext import ScrolledText

import requests

# Static Variables
paper_versions: list = []
paper_builds: dict = {}


# Static Methods
def get_projects() -> list:
    if os.path.exists("TestServers"):
        projects = []
        for project in os.listdir(f"TestServers"):
            if os.path.isdir(f"TestServers/{project}"):
                projects.append(project)
        return projects
    else:
        return []


def get_versions(project: str) -> list:
    if os.path.exists(f"TestServers/{project}"):
        versions = []
        for version in os.listdir(f"TestServers/{project}"):
            if os.path.isdir(f"TestServers/{project}/{version}"):
                versions.append(version)
        return versions
    else:
        return []


def get_project_versions(project: str) -> list:
    if os.path.exists("TestServers/" + project):
        return os.listdir("TestServers/" + project)
    else:
        return []


def get_jar_path(project: str, platform: str, version: str) -> str:
    if os.path.exists(f"TestServers/{project}/{version}-{platform}"):
        for filename in os.listdir(f"TestServers/{project}/{version}-{platform}"):
            if re.search(f"{platform}-{version}-[0-9]+\\.jar", filename):
                return filename
    return ""


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
    paper_builds[version] = builds
    return builds


def get_jar(platform: str, version: str, build: str) -> str:
    # Make sure cache folder exists
    os.makedirs("cache", exist_ok=True)
    if not os.path.exists(f"cache/{platform}-{version}-{build}.jar"):
        r = requests.get(
            f"https://api.papermc.io/v2/projects/paper/versions/1.19.4/builds/521/downloads/{platform}-{version}-{build}.jar")
        if not r.status_code == 200:
            messagebox.showerror("Download Failed!", f"{r.status_code}: {r.reason}"
                                                     f"\nFailed to download {platform}-{version}-{build}.jar")
            return None
        open(f"cache/{platform}-{version}-{build}.jar", 'wb').write(r.content)
    return f"cache/{platform}-{version}-{build}.jar"


def set_plugin_locations(project: str, locations) -> None:
    jsonDict = {}
    if os.path.exists(f"TestServers/{project}/meta.json"):
        with open(f"TestServers/{project}/meta.json", 'r') as f:
            json_string = f.read()
            jsonDict = json.loads(json_string)
    jsonDict['plugin_locations'] = list(locations)
    with open(f"TestServers/{project}/meta.json", "w") as f:
        json.dump(jsonDict, f)


def get_plugin_locations(project: str) -> list:
    if os.path.exists(f"TestServers/{project}/meta.json"):
        with open(f"TestServers/{project}/meta.json", 'r') as f:
            json_string = f.read()
            jsonDict: dict = json.loads(json_string)
            if 'plugin_locations' in jsonDict.keys():
                return jsonDict['plugin_locations']
    return []


class Main:
    # noinspection PyTypeChecker
    def __init__(self):
        # Persistent variables
        self.restart_server_button = None
        self.should_restart = None
        self.copy_and_restart_button = None
        self.select_plugin_button = None
        self.create_version_button: Button = None
        self.reader_thread: Thread = None
        self.console_buffer: list = []
        self.build_dropdown: Spinbox = None
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
        self.server_process: subprocess.Popen = None
        self.platform: str = ''
        self.version: str = ''
        self.build: str = ''
        self.log_content: str = ''
        self.previous_log_content: str = ''
        self.page: str = ''
        self.project: str = ''

        # Create root frame / widget
        self.root = Tk()
        self.root.geometry("800x500")

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
            Button(self.root, text=project, command=lambda proj=str(project): self.select_project(proj)).pack()
        button = Button(self.root, text="Create New Project", command=self.open_new_project_page)
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
        for version in get_versions(self.project):
            Button(self.left_frame, text=version, command=lambda ver=str(version): self.select_version(ver)).pack()
        new_label = Label(self.right_frame, text="Create a version")
        new_label.grid(row=0, column=0)
        self.platform_dropdown = OptionMenu(self.right_frame, StringVar(self.right_frame), "Paper", "Purpur", "Folia",
                                            command=self.on_select_platform)
        self.platform_dropdown.grid(row=1, column=0)
        self.version_dropdown = OptionMenu(self.right_frame, StringVar(self.right_frame), "")
        self.version_dropdown.grid(row=2, column=0)
        self.build_dropdown = Spinbox(self.right_frame, from_=0, to=0)
        self.build_dropdown.grid(row=3, column=0)

    def open_project_page(self):
        self.clear_page()
        self.page = "project"
        if self.project == '':
            self.open_new_project_page()
            return
        if self.version == '':
            self.open_select_version_page()
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

        def select_plugin_files():
            files = filedialog.askopenfilenames(parent=self.left_frame, title="Select files")
            set_plugin_locations(self.project, files)

        def copy_and_restart():
            os.makedirs(f"TestServers/{self.project}/{self.version}-{self.platform}/plugins", exist_ok=True)
            print(f"TestServers/{self.project}/{self.version}-{self.platform}/plugins")
            for path in get_plugin_locations(self.project):
                if os.path.exists(path):
                    shutil.copy(
                        path,
                        f"TestServers/{self.project}/{self.version}-{self.platform}/plugins"
                    )
            self.stop_server(should_restart=True)

        # Buttons
        self.copy_and_restart_button = Button(self.left_frame, text="Copy Plugin and Restart", command=copy_and_restart)
        self.copy_and_restart_button.pack(padx=3, pady=3)
        self.select_plugin_button = Button(self.left_frame, text="Select Plugin Files", command=select_plugin_files)
        self.select_plugin_button.pack(padx=3, pady=3)
        self.start_server_button = Button(self.left_frame, text="Start Server", command=self.start_server)
        self.start_server_button.pack(padx=3, pady=3)
        self.restart_server_button = Button(self.left_frame, text="Restart Server", command=lambda: self.stop_server(True))
        self.restart_server_button.pack(padx=3, pady=3)
        self.stop_server_button = Button(self.left_frame, text="Stop Server", command=lambda: self.stop_server(False))
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

    # Project Creation
    def create_project(self, event):
        self.project = self.new_project_entry.get()
        if not os.path.exists("TestServers/" + self.project):
            os.makedirs("TestServers/" + self.project, exist_ok=True)
        self.open_project_page()

    def select_project(self, project):
        self.project = project
        self.open_select_version_page()

    def select_version(self, full_version: str):
        self.platform = full_version.split('-', 1)[1]
        self.version = full_version.split('-', 1)[0]
        self.open_project_page()

    def on_select_platform(self, platform: str):
        self.platform = platform.lower()
        if self.platform == "paper":
            self.version_dropdown.destroy()
            default = StringVar(self.right_frame)
            if not get_paper_versions() == []:
                default.set(get_paper_versions()[0])
            self.version_dropdown = OptionMenu(self.right_frame, default, *get_paper_versions(),
                                               command=self.on_select_version)
            self.version_dropdown.grid(row=2, column=0)
            # Get build info for default selection
            self.on_select_version(get_paper_versions()[0])

    def on_select_version(self, version):
        self.version = version
        self.build_dropdown.destroy()
        builds = get_paper_builds(version)
        default_build = IntVar()
        default_build.set(builds[len(builds) - 1])
        self.build_dropdown = Spinbox(self.right_frame, values=builds, from_=builds[0], to=builds[len(builds) - 1],
                                      command=self.on_select_build)
        self.build_dropdown.config(textvariable=default_build)
        self.build = builds[len(builds) - 1]

        def on_deselect():
            self.root.focus()
            if int(self.build_dropdown.get()) > builds[len(builds) - 1]:
                latest_build = IntVar()
                latest_build.set(builds[len(builds) - 1])
                self.build_dropdown.config(textvariable=latest_build)
            elif int(self.build_dropdown.get()) < builds[0]:
                oldest_build = IntVar()
                oldest_build.set(builds[0])
                self.build_dropdown.config(textvariable=oldest_build)

        self.build_dropdown.bind("<Return>", lambda x: on_deselect())
        self.build_dropdown.grid(row=3, column=0)
        self.create_version_button = Button(self.right_frame, text="Create Version", command=self.create_version)
        self.create_version_button.grid(row=4, column=0)

    def on_select_build(self, build):
        self.build = build

    def create_version(self):
        if self.project == '':
            return
        os.makedirs(f"TestServers/{self.project}/{self.version}-{self.platform}", exist_ok=True)
        shutil.copy(
            get_jar(self.platform, self.version, self.build),
            f"TestServers/{self.project}/{self.version}-{self.platform}/{self.platform}-{self.version}-{self.build}.jar"
        )
        # Copy EULA
        if os.path.exists("eula.txt"):
            shutil.copy(
                "eula.txt",
                f"TestServers/{self.project}/{self.version}-{self.platform}/eula.txt"
            )
        self.open_project_page()

    # Window functions
    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.kill_server()
            self.root.destroy()

    # Widget functions
    def start_server(self):
        self.should_restart = False
        # Clear displayed log
        self.console_output.config(state=NORMAL)
        self.console_output.delete("1.0", END)
        self.console_output.config(state=DISABLED)
        # Start server process
        self.server_process = subprocess.Popen(
            f'java -jar {get_jar_path(self.project, self.platform, self.version)} --nogui',
            cwd=f"TestServers/{self.project}/{self.version}-{self.platform}",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )

        def console_reader(stdout, buffer) -> None:
            while True:
                line = stdout.readline()
                if line:
                    buffer.append(line)
                else:
                    break
                time.sleep(0.1)

        self.console_buffer = []
        self.reader_thread = Thread(target=console_reader, args=(self.server_process.stdout, self.console_buffer))
        self.reader_thread.daemon = True
        self.reader_thread.start()

    def stop_server(self, should_restart: bool):
        self.should_restart = should_restart
        if self.server_process is not None:
            self.server_process.stdin.write(bytes("stop" + '\r\n', 'ascii'))
            self.server_process.stdin.flush()

    def kill_server(self):
        self.should_restart = False
        if self.server_process is not None:
            self.server_process.kill()
            self.server_process = None

    def send_command(self, event):
        # Only send command and clear entry box if server is running
        if self.server_process is not None:
            command = self.console_entry.get()
            if command:
                self.server_process.stdin.write(bytes(command + '\r\n', 'ascii'))
                self.server_process.stdin.flush()
                self.console_entry.delete(0, 'end')

    # GUI loop
    def customLoop(self):
        if self.page == "project":
            # Check if fully scrolled down before writing to console
            fully_scrolled_down = self.console_output.yview()[1] == 1.0

            # Write to console
            count = 0
            while self.console_buffer and count < 25:
                count += 1
                self.console_output.config(state=NORMAL)
                self.console_output.insert(END, self.console_buffer.pop(0))
                self.console_output.config(state=DISABLED)

            # Scroll console if it was already scrolled all the way down
            if fully_scrolled_down:
                self.console_output.see(END)

            # Check if server is still running and if it should restart
            if self.server_process and self.server_process.poll() is not None and self.should_restart:
                self.should_restart = False
                self.server_process = None
                self.start_server()

        # Recall loop
        self.root.after(10, self.customLoop)


if __name__ == "__main__":
    main = Main()
    # Start custom gui loop
    main.customLoop()
    main.root.mainloop()

import shlex
from abc import ABC
from html.parser import HTMLParser
from subprocess import run, CalledProcessError

supported_distros = ("focal", "bullseye", "hirsute")
current_distro = ""

arm64_cpus = ("armv8l", "aarch64", "arm64")
amd64_cpus = ("x86_64", "x86-64", "x64", "amd64")
current_cpu = ""

dependencies = ("python3", "curl", "lxc")

curl = "curl --proto '=https' --tlsv1.2 -Sf"


def execute_bash(bash_command, return_output=True):
    bash_output = run(
        shlex.split(f"bash -c '{bash_command}'"),
        capture_output=return_output,
        text=True, check=True
    )
    return bash_output.stdout.strip() if (return_output and bash_output.stdout) else None


def show_message_and_exit(message="\nexiting due to previous error"):
    input(f"{message}\npress enter to exit..")
    exit()


# helper functions to meet prerequisites
def check_cpu():
    global arm64_cpus
    global amd64_cpus
    global current_cpu

    try:
        current_cpu = execute_bash("uname -m")
    except CalledProcessError:
        current_cpu = input("please enter your cpu type: ")

    if current_cpu in arm64_cpus:
        current_cpu = "arm64"
    elif current_cpu in amd64_cpus:
        current_cpu = "amd64"
    else:
        show_message_and_exit(
            f"unsupported cpu type: {current_cpu}\
                supported cpu types: {arm64_cpus}, {amd64_cpus}"
        )


def check_distro():
    global supported_distros
    global current_distro

    try:
        current_distro = execute_bash("lsb_release -sc")
    except CalledProcessError:
        current_distro = input("please enter your distribution codename: ")

    if current_distro not in supported_distros:
        show_message_and_exit(
            f"unsupported distribution codename: {repr(current_distro)}"
            f"\nsupported distribution codenames: {supported_distros}"
        )


def check_wayland():
    try:
        if execute_bash("echo $XDG_SESSION_TYPE") != "wayland":
            show_message_and_exit("only wayland is supported")
    except CalledProcessError:
        if input("are you on wayland? [y/N]: ") != "y":
            show_message_and_exit("only wayland is supported")


def install_dependencies():
    global dependencies

    install_command = f"sudo apt-get install -q {' '.join(dependencies)}"
    print(install_command)
    try:
        execute_bash(install_command, return_output=False)
    except CalledProcessError:
        show_message_and_exit("failed to install dependencies")


# unified install function
def unified_install():
    global current_distro
    global curl

    bash_commands = (
        f"sudo {curl} https://repo.waydro.id/waydroid.gpg --output "
        "/usr/share/keyrings/waydroid.gpg",

        f"echo 'deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydro.id/ {current_distro} main' | "
        f"sudo tee /etc/apt/sources.list.d/waydroid.list >/dev/null",

        "sudo apt-get -q update"
    )

    for bash_command in bash_commands:
        try:
            execute_bash(bash_command, return_output=False)
        except CalledProcessError:
            show_message_and_exit()


# helper functions to download/install packages at repo.waydro.id/erfan/{current_distro}
class WaydrHTMLParser(HTMLParser, ABC):
    def __init__(self):
        super(WaydrHTMLParser, self).__init__()
        self.reset()
        self.packages = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, link in attrs:
                if name == "href" and link.endswith(".deb"):
                    self.packages.append(link)


def install_repo_packages():
    global current_cpu
    global current_distro
    global curl

    repo_url = f"https://repo.waydro.id/erfan/{current_distro}/"
    download_path = f"~/Downloads/darth_waydr/{current_distro}/"

    waydr_html_parser = WaydrHTMLParser()
    waydr_html_parser.feed(execute_bash(f"{curl} {repo_url}"))

    for package in waydr_html_parser.packages:
        if "waydroid" not in package:
            if current_cpu in package or (current_cpu == "arm64" and "all" in package):
                try:
                    print(f"\n{package}")

                    execute_bash(f"mkdir -p {download_path}")
                    execute_bash(f"{curl} {repo_url}{package} --output {download_path}{package}", return_output=False)
                    execute_bash(f"sudo dpkg -i {download_path}{package} || sudo apt-get install -f",
                                 return_output=False)
                except CalledProcessError:
                    show_message_and_exit()


# helper functions to install and initialize waydroid
def desktop_install():
    bash_command = "sudo apt-get -q install waydroid && sudo waydroid init"
    try:
        execute_bash(bash_command, return_output=False)
    except CalledProcessError:
        show_message_and_exit()


def create_alias():
    waydroid_aliases = (
        "alias waydroid-stop='sudo waydroid session stop && sudo waydroid container stop'",

        "alias waydroid-start='waydroid-stop 2>/dev/null && sudo systemctl start waydroid-container && waydroid "
        "session start'",

        "alias waydroid-start-full='waydroid-stop 2>/dev/null && sudo systemctl start waydroid-container && waydroid "
        "show-full-ui' "
    )
    for waydroid_alias in waydroid_aliases:
        print("\n", waydroid_alias)

    if input("\ncreate these aliases [Y/n]: ") != "n":
        try:
            with open(f"{execute_bash('echo $HOME')}/.bashrc", "r+") as bashrc_file:
                bashrc_data = bashrc_file.read()

                for waydroid_alias in waydroid_aliases:
                    if waydroid_alias not in bashrc_data:
                        bashrc_file.write(f"\n{waydroid_alias}\n")
            print("created aliases")
            print("restart shell/terminal if you cannot access aliases")
        except (CalledProcessError, FileNotFoundError):
            print("failed to create aliases")
    else:
        print("skipping alias creation")


if __name__ == "__main__":
    print("\nDarth Waydr")

    print("\nPrerequisites")
    check_cpu()
    check_distro()
    check_wayland()
    install_dependencies()

    print("\nUnified install")
    unified_install()

    print("\nRepo packages install")
    install_repo_packages()

    print("\nDesktop install")
    desktop_install()

    print("\nCreate aliases")
    create_alias()

    print("\nEnjoy waydroid!")

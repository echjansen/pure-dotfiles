#!/usr/bin/env python3
import sys
import argparse
import subprocess
from configparser import ConfigParser, ExtendedInterpolation

class Msg:

    status_colors = {
        0: 1,
        1: 4,
        2: 3,
        3: 2,
        4: 4,
        5: 4,
        6: 3
    }

    status_mgs = {
        0: '    ',
        1: 'WAIT',
        2: 'DONE',
        3: 'FAIL',
        4: 'WARN',
        5: 'INFO',
        6: ' OK '
    }

    def __init__ (self):
        pass

    # Writes a status message; see status_mgs & status_colors. Examples:
    #   >> Using log engine v2.0
    #   >> [ WAIT ] Fetching latest data...
    #   >> [  OK  ] Started NetworkManager service
    #   >> [ FAIL ] ...
    def write_msg(self, msg, status=0, override_newline=-1):
        if status > 0:
            color = self.status_colors.get(status)
            status_msg = self.status_mgs.get(status, 0)
            self.write(f'§{color}>> [ {status_msg} ] ') # e.g. '>> [ WAIT ] '
        else:
            self.write('§7>> ') # '>> '

        new_ln = True if override_newline == -1 and status > 1 else False
        new_ln = True if override_newline == 1 else new_ln
        self.write(msg + ('\n' if new_ln else ''))

    # Writes back to the current status message line to update the appearance
    #   write_status(0, 0)
    #   '>> [ DONE ]'
    #   write_status(1, 0, 4)
    #   '>> [ WARN ]'
    def write_status(self, ret_val=0, expected_val=0, error_status=3):
        if ret_val == expected_val:
            status_msg = self.status_mgs.get(2)
            self.write_ln(f'\r§3>> [ {status_msg} ]')
        else:
            color = self.status_colors.get(error_status)
            status_msg = self.status_mgs.get(error_status)
            self.write_ln(f'\r§{color}>> [ {status_msg} ]')

    # Writes text to stdout with optional coloring; see color_str()
    def write(self, text):
        if '\\§' in text: text = text.replace('\\§', '§') # '\§' => '§'
        elif '§' in text: text = self.color_str(text)

        sys.stdout.write(text)
        sys.stdout.flush()

    # Writes a line of text to stdout with optional coloring; see color_str()
    def write_ln(self, text='', new_line_count=1):
        for _ in range(0, new_line_count):
            text += '\n'
        self.write(text)

    # Returns a string with parsed terminal output forecolor; usage:
    # e.g. color_str("§2red §0reset §5blue")

    # Colors:
    # 0 = Default (white fg, black bg)
    # 1 = Black
    # 2 = Red
    # 3 = Green
    # 4 = Yellow
    # 5 = Blue
    # 6 = Magenta
    # 7 = Cyan
    # 8 = White
    def color_str(self, string, reset=True):
        if '§' in string: # Possible color definition found
            for f in range(0, 9): # Forecolor only: (0-8)
                match = f'§{str(f)}' # e.g. '§2'
                if match not in string: # match not found => check next color
                    continue
                fg = '0' # default fg to white (37)
                if f != 0: # update fg to use defined color
                    fg = str(29 + f)
                string = string.replace(match, f'\033[0;{fg}m') # e.g. '\e[0;32m'
        if reset:
            string += '\033[0m'
        return string


class Cmd(Msg):
    """A class that executes bash command lines"""

    def __init__(self):
        pass

    # Run a command on the shell with an optional io stream
    # io_stream_type: 0 = none, 1 = stdout, 2 = logged, 3 = all_supressed
    # Returns: command exit code / output when io_stream_type=2
    def exec(self, cmd, msg, exec_user='', log_cmd=True, io_stream_type=0):
        user_exec = cmd.startswith('$ ')
        exec_cmd = cmd

        if user_exec:
            cmd = cmd[2:] # Remove '$ ' from user_exec commands
            exec_cmd = f'sudo {cmd}'

        use_stdout = (io_stream_type == 1)
        logged = (io_stream_type == 2)
        suppress = (io_stream_type == 3)

        if log_cmd and io_stream_type % 2 == 0: # Log executed command line ()
            start = '# ' + (f'({exec_user}) $ ' if user_exec else '')
            self.log(f'\n{start}{cmd}') # e.g. '# pacman -Syu'

        end = ''

        if suppress or logged:
            path = '/tmp'
            log_path = f'{path}/install.log' # e.g. '/tmp/install.log' or '/install.log' in chroot
            end = ' ' + f'&>>{log_path}' if logged and log_cmd else '&>/dev/null'

        cmd = exec_cmd + end
        self.write_msg(msg, 1)
        if use_stdout:
            res = subprocess.run(cmd, shell=True, text=True, encoding='utf-8', capture_output=use_stdout)
        else:
            res = subprocess.run(cmd, shell=True)

        if log_cmd and io_stream_type % 2 == 0 and res.returncode != 0:
            self.log(f'\n# Command non-zero exit code: {res.returncode}')
            self.write_status(4)
        else:
            self.write_status()

        returns = res.stdout if use_stdout else res.returncode
        return returns

    def exec_output(self, cmd, msg='', exec_user='', log_cmd=True):
        '''Execute command and return all output'''
        return self.exec(cmd, msg, exec_user, log_cmd, 1)

    def exec_log(self, cmd, msg='', exec_user='', log_cmd=True):
        '''Execute a shell command and record all output in log file'''
        return self.exec(cmd, msg, exec_user, log_cmd, 2)

    def exec_suppress(self, cmd, msg='', exec_user=''):
        '''Execute a shell commands a suppress all output'''
        return self.exec(cmd, msg, exec_user, False, 3)

    def exists(self, cmd, msg=''):
        '''Check weather a command is available on the system'''
        ret_val = self.exec_suppress(f'type {cmd}', msg) # command -v
        return (ret_val == 0)

    def log(self, text, append=True):
        '''Log a new line to /{tmp}/install.log'''
        path = '/tmp'
        f_path = path + '/install.log'
        try:
            mode = 'a' if append else 'w'
            with open(f_path, f'{mode}+') as f:
                f.write(text)
                return 0
        except:
            return 1

class Pkg(Cmd):

    def __init__(self):
        pass

    # Refresh local package database cache
    # Quit script execution on error
    def refresh_cache(self, force_refresh=False, quit_on_fail=True):
        cmd = 'yay -Sy'
        cmd += 'y' if force_refresh else ''

        ret_val = self.exec_log(cmd, "Refreshing pacman database cache.")

        if ret_val != 0 and quit_on_fail:
            exit_code = 8 if force_refresh else 7
            # 7 = Couldn't synchronize databases,
            # 8 = Force-refresh failed
            exit(exit_code)
        return ret_val

    # Install packages from the Arch repositories (core, extra, community)
    # or optionally a local package with the absolute path defined
    # Returns: pacman exit code
    def install(self, pkgs, feature='', only_needed=True):
        """Install packages (space separated)"""
        pac_args = '--needed' if only_needed else ''
        local = ('/' in pkgs)

        if len(pac_args) > 0: pac_args = ' ' + pac_args.strip()
        action = 'U' if local else 'S'
        if feature != '':
            ret_val = self.exec_log(f'yay -{action} --noconfirm --noprogressbar {pac_args} {pkgs}', f'Installing {feature}: {pkgs}')
        else:
            ret_val = self.exec_log(f'yay -{action} --noconfirm --noprogressbar {pac_args} {pkgs}', f'Installing {pkgs}')
        return ret_val

class Service(Cmd):

    def __init__(self):
        pass

    def enable(self, services, feature=''):
        """Enable service(s) (space seperated"""
        if feature != '':
            ret_val = self.exec_log(f'$ systemctl enable {services}', f'Enabling {feature}: {services}')
        else:
            ret_val = self.exec_log(f'$ systemctl enable {services}', f'Enabling: {services}')
        return ret_val

    def start(self, services, feature=''):
        """Start service(s) (space seperated"""
        if feature != '':
            ret_val = self.exec_log(f'$ systemctl restart {services}', f'Starting {feature}: {services}')
        else:
            ret_val = self.exec_log(f'$ systemctl restart {services}', f'Starting: {services}')
        return ret_val

def main():

    parser = argparse.ArgumentParser(
        description='Install user required packages and services.\n\n'
                    'This script requires one argument:\n'
                    '1. Path to configuration file in ~INI~ format.\n',
        epilog='''Install user packages example:
        python install.py install/core
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('config', type=str, nargs='+',
                        help="path to one or more configuration files in ~INI~ format")

    args = parser.parse_args()
    parser = ConfigParser(interpolation=ExtendedInterpolation())
    pkg = Pkg()
    srv = Service()

    if not pkg.exists("yay", "Checking if AUR helper exists."):
        pkg.write_msg('Please install the AUR helper ~yay~', 3)
        exit()

    # Refresh the pacman / aur package definition cache
    pkg.refresh_cache()

    # Load the list of install file(s) - 1 is the minimum required
    config_files = args.config

    for config_file in config_files:
        # Parse the provided install file
        print()
        parser.clear()
        parser.read_file(open(config_file))
        pkg.write_msg(f'Processing install file {config_file}:', 5)

        # Install features defined in the 'pacman' section
        if len(parser["pacman"])>0:pkg.write_msg("Installing archlinux package(s):.", 5)
        for feature in parser['pacman']:
            pkg.install(parser['pacman'][feature], [feature])

        # Install features defined in the 'aur' section
        if len(parser["aur"])>0:pkg.write_msg("Installing AUR package(s):.", 5)
        for feature in parser['aur']:
            pkg.install(parser['aur'][feature], [feature])

        # Enable and restart services
        if len(parser["service"])>0:pkg.write_msg("Enabling and Starting service(s):.", 5)
        for feature in parser['service']:
            service = parser['service'][feature]
            srv.enable(service, feature)
            srv.start(service, feature)

        # Execute bash script
        if len(parser["script"])>0:pkg.write_msg("Executing bash script(s):.", 5)
        for feature in parser['script']:
            script = parser['script'][feature]
            pkg.exec_log(script, f'Executing {script}')

    print()
    pkg.write_msg("Check ~/tmp/install.log~ for full installation output.", 5)

if __name__ == "__main__":
    main()

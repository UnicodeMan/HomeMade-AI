from ..utils import drop_privileges
import os
import subprocess
import re
import asyncio
import tempfile
import signal
import psutil
from pathlib import Path
import shlex

class ShellEnvironment:

    def __init__(self, working_directory="/data"):
        self.working_directory = working_directory

        # Activate the venv
        self.venv_dir = os.path.expanduser("/data/venv")
        self.activate_script = os.path.join(self.venv_dir, "bin", "activate")


    async def extract_commands(self, response):
        """Extract commands from response with shell type"""
        commands = {
            "bash": [],
            "python": [],
            "reset": []
        }

        # Extract bash commands
        bash_pattern = r'\[EXECUTE\](.*?)\[/EXECUTE\]'
        commands["bash"] = re.findall(bash_pattern, response, re.DOTALL)

        # Extract Python commands
        python_pattern = r'\[PYTHON\](.*?)\[/PYTHON\]'
        commands["python"] = re.findall(python_pattern, response, re.DOTALL)

        # Extract reset commands
        reset_pattern = r'\[RESET:(.*?)\]'
        commands["reset"] = re.findall(reset_pattern, response)

        return commands

    async def execute_commands(self, commands: dict) -> str:
        """
        Execute commands in their respective environments based on shell type.

        Args:
            commands (dict): A dictionary with keys "bash", "python", and "reset",
                             containing lists of commands to execute.

        Returns:
            str: Aggregated results of command execution.
        """
        if not isinstance(commands, dict):
            raise TypeError("Expected 'commands' to be a dictionary with keys 'bash', 'python', and 'reset'.")

        results = []
        print("in execute_commands function:")
        print(commands)
        # Execute bash commands
        if "bash" in commands and commands["bash"]:
            for command in commands["bash"]:
                # Split multiline commands into single lines
                command_lines = command.splitlines()
                
                escaped_command = shlex.quote('\n'.join(command_lines))  


                # Append the quoted_command to each line

                # Execute all lines at once and capture output
                stdout, stderr = await self.execute_bash(self.venv_dir, command_lines, self.working_directory)

                # Escape newlines in stdout and stderr for logging
                escaped_stdout = stdout.strip().replace("\n", "\\n") if stdout else "None"
                escaped_stderr = stderr.strip().replace("\n", "\\n") if stderr else "None"

                results.append(
                    f"Bash command executed:\n"
                    f"Command: {escaped_command}\n"  # Consider how to represent the full command here
                    f"Output: {escaped_stdout}\n"
                    f"Errors: {escaped_stderr}\n"
                )
                print(f"Bash command executed:\n"
                      f"Command: {escaped_command}\n"  # Consider how to represent the full command here
                      f"Output: {escaped_stdout}\n"
                      f"Errors: {escaped_stderr}\n")
        # Execute Python commands
        if "python" in commands and commands["python"]:
            for command in commands["python"]:
                stdout, stderr = await self.execute_python(command)  # Use self.execute_python
                escaped_command = command.replace("\n", "\\n")
                escaped_stdout = stdout.strip().replace("\n", "\\n") if stdout else "None"
                escaped_stderr = stderr.strip().replace("\n", "\\n") if stderr else "None"

                results.append(
                    f"Python command executed:\n"
                    f"Command: {escaped_command}\n"
                    f"Output: {escaped_stdout}\n"
                    f"Errors: {escaped_stderr}\n"
                )
                print(
                    f"Python command executed:\n"
                    f"Command: {escaped_command}\n"
                    f"Output: {escaped_stdout}\n"
                    f"Errors: {escaped_stderr}\n"
                )

        # Handle reset commands
        if "reset" in commands and commands["reset"]:
            return ""
            for reset_target in commands["reset"]:
                result = self.reset_shell(reset_target)  # Use self.reset_shell
                results.append(f"Reset executed: {reset_target}\nResult: {result}\n")
                print(f"Reset executed: {reset_target}\nResult: {result}\n")
        print("\n".join(results))

        return "\n".join(results)
    async def execute_bash(self, venv_dir, lines: list[str], working_directory="."):
        stdout = stderr = None
        try:
            full_command = [os.path.join(venv_dir, 'bin/bash'), '-c', '\n'.join(lines)]

            # Create a temporary file for the Python code
            activate_script = os.path.join(self.venv_dir, "bin", "activate")
            wrapper_script = "/app/lib/shell_environment/wrapper_script.sh"
            temp_file = None  # Initialize temp_file here
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tf:
                tf.writelines([f". {activate_script}\n",
                              f"cd {working_directory}\n",
                           * [f"{line}\n" for line in lines]  # Expand lines with newlines
                ])
                temp_file = tf.name
            subprocess.run(["chown", "ai:ai", temp_file], check=True)
            subprocess.run(["chmod", "+x", temp_file], check=True)
            # Construct the command to run as ai user
            #safe_command = shlex.quote(f". {activate_script}; {command}")
            run_as_ai = (
            f"{temp_file}")

            process = await asyncio.create_subprocess_exec(
                run_as_ai,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_directory,
                shell=False,
                preexec_fn=drop_privileges(1001, 1001)  # Pass the callable returned by drop_privileges
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=90)
                stdout_str = stdout.decode() if stdout else ""
                stderr_str = stderr.decode() if stderr else ""
                return stdout_str, stderr_str

            except asyncio.TimeoutError:
                print("Bash execution timed out")
                try:
                # Kill the entire process tree
                    self.kill_process_tree(process.pid)  # This is to ensure no zombie processes or memory leaks occur
            
                # Ensure the main process is terminated
                    if process.returncode is None:
                        await process.kill()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        pass
                
                except ProcessLookupError:
                    pass
        
                return "", "Error: Bash execution timed out"
        except Exception as e:
           return "", f"Error: {e}"
        finally:
                # Clean up temporary file
            try:
                subprocess.run(["rm", "-f", temp_file], check=True)
                """subprocess.run(["rm", "-f", temp_file_wrapper], check=True)"""
            finally:
                pass
            if stdout:
                print(f"Command finished. Stdout: {stdout.decode()}")
            if stderr:
                print(f"Command finished. Stderr: {stderr.decode()}")
    async def execute_python(self, command, timeout=90):
        stdout = stderr = None
        temp_file = None
        try:
            # Create a temporary file for the Python code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
                tf.write(f"#!{self.venv_dir}/bin/python3\n"
                        f"import os\n"
                        f"os.chdir('{self.working_directory}')\n"
                        f"{command}")
                temp_file = tf.name

        # Ensure proper permissions
            subprocess.run(["chown", "ai:ai", temp_file], check=True)
            subprocess.run(["chmod", "+x", temp_file], check=True)

            # Construct command
            run_as_ai = f"{temp_file}"

            process = await asyncio.create_subprocess_exec(
                run_as_ai,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory,
                shell=False,
                preexec_fn=drop_privileges(1001, 1001)
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                stdout_str = stdout.decode() if stdout else ""
                stderr_str = stderr.decode() if stderr else ""
                return stdout_str, stderr_str

            except asyncio.TimeoutError:
                print(f"Python execution timed out after {timeout} seconds")
                try:
                    # Kill the entire process tree
                    self.kill_process_tree(process.pid)  # This is to ensure no zombie processes or memory leaks occur

                    # Ensure the main process is terminated
                    if process.returncode is None:
                        await process.kill()
                        try:
                            await asyncio.wait_for(process.wait(), timeout=5)
                        except asyncio.TimeoutError:
                            pass
                            
                except ProcessLookupError:
                    pass
                    
                return "", f"Error: Python execution timed out after {timeout} seconds"

        except Exception as e:
            return "", f"Error: {e}"

        finally:
            # Clean up temporary file
            try:
                subprocess.run(["rm", "-f", temp_file], check=True)
            finally:
                pass
            if stdout:
                print(f"Command finished. Stdout: {stdout.decode()}")
            if stderr:
                print(f"Command finished. Stderr: {stderr.decode()}")
    def reset_environment_variables(self):
        """Resets environment variables to their default state."""

        try:
            # Get default environment variables
            result = subprocess.run(
                ['env', '-i', 'bash', '-c', 'env'],  # Use 'env -i' to start with a clean environment
                capture_output=True,
                text=True,
                check=True  # Raise an exception if the command fails
            )

            # Parse and set environment variables
            for line in result.stdout.splitlines():
                key, value = line.split('=', 1)
                os.environ[key] = value

            print("Environment variables reset successfully.")

        except subprocess.CalledProcessError as e:
            print(f"Error resetting environment variables: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def kill_process_tree(self, pid): # This function is required to ensure no zombie processes and memory leaks happen
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
        
            # Kill children first
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
                    
            # Kill parent
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
                
            # Wait for processes to be killed
            gone, alive = psutil.wait_procs(children + [parent], timeout=3)

            # Force kill if still alive
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            pass


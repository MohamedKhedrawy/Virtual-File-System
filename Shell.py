import os
from FsConstants import FsConstants


class Shell:
    def __init__(self, fileSystem, directory):
        self.currentPath = "H:/"
        self.directory = directory
        self.fileSystem = fileSystem
        self.currentCluster = FsConstants.ROOT_DIR_FIRST_CLUSTER
        self.pathStack = []  # Stack to track parent clusters for cd ..

    def run(self):
        """Main shell loop."""
        print("Type 'help' for available commands.")
        print()
        
        while True:
            try:
                userInput = input(self.currentPath + "> ")
                userInput = userInput.strip()
                
                if not userInput:
                    continue
                
                tokens = userInput.split(" ", 1) 
                command = tokens[0].lower()
                args = tokens[1] if len(tokens) > 1 else ""
                
                match command:
                    case "exit":
                        self.exit()
                        return
                    case "help":
                        self.help()
                    case "ls":
                        self.ls()
                    case "cd":
                        self.cd(args)
                    case "clear":
                        self.clear()
                    case "cp":
                        self.cp(args)
                    case "mv":
                        self.mv(args)
                    case "mkdir":
                        self.mkdir(args)
                    case "rmdir":
                        self.rmdir(args)
                    case "rm":
                        self.rm(args)
                    case "touch":
                        self.touch(args)
                    case "cat":
                        self.cat(args)
                    case "echo":
                        self.echo(args)
                    case "rename":
                        self.rename(args)
                    case _:
                        print(f"Unknown command: {command}. Type 'help' for available commands.")
            except EOFError:
                print("\nExiting shell...")
                return
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit the shell.")
            except Exception as e:
                print(f"Error: {e}")

    def exit(self):
        """Exit the shell."""
        print("Exiting shell... ")

    def help(self):
        """Display available commands."""
        print("""
Available commands:
  help              - Show this help message
  ls                - List directory contents
  cd <dir>          - Change directory (use '..' for parent)
  mkdir <name>      - Create a new directory
  rmdir <name>      - Remove an empty directory
  touch <name>      - Create a new empty file
  rm <name>         - Delete a file
  cat <file>        - Display file contents
  echo <text> > <file> - Write text to a file
  rename <old> <new> - Rename a file or directory
  cp <src> <dest>   - Copy a file
  mv <src> <dest>   - Move a file
  clear             - Clear the screen
  exit              - Exit the shell
""")

    def ls(self):
        """List directory contents."""
        entries = self.directory.readDirectoryEntry(self.currentCluster)
        
        if not entries:
            print("(empty directory)")
            return
        
        for entry in entries:
            print(entry.name)

    def cd(self, path):
        """Change current directory."""
        path = path.strip()
        
        if not path:
            print("Usage: cd <directory>")
            return
        
        if path == "..":
            # Go to parent directory
            if self.pathStack:
                # Updates self.currentCluster to the target directory's first cluster
                self.currentCluster, parentPath = self.pathStack.pop()
                # Updates self.currentPath to reflect the new directory path
                self.currentPath = parentPath
            else:
                print("Already at root directory")
            return
        
        if path == ".":
            # Already in current directory, do nothing
            return
        
        # Find the directory entry
        de = self.directory.findDirectoryEntry(self.currentCluster, path)
        if not de:
            print(f"Directory not found: {path}")
            return
        
        if de.attr != 0x01:
            print(f"Not a directory: {path}")
            return
        
        # Pushes current location onto pathStack before navigation
        self.pathStack.append((self.currentCluster, self.currentPath))
        self.currentCluster = de.firstCluster
        # update currentPath
        self.currentPath = self.currentPath.rstrip("/") + "/" + de.name.strip() + "/"

    def clear(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    
    def cp(self, args):
        """Copy a file."""
        parts = args.split()
        if len(parts) != 2:
            print("Usage: cp <source> <destination>")
            return
        
        source, dest = parts
        
        # Resolve source path
        sourceCluster, sourceFile = self._resolvePath(source)
        if sourceCluster is None or sourceFile is None:
            print(f"Source path invalid: {source}")
            return
        
        # Resolve destination path
        destCluster, destFile = self._resolvePath(dest)
        if destCluster is None or destFile is None:
            print(f"Destination path invalid: {dest}")
            return
        
        if self.fileSystem.copyFile(sourceCluster, sourceFile, destCluster, destFile):
            print(f"Copied {source} to {dest}")

    def mv(self, args):
        """Move a file."""
        parts = args.split()
        if len(parts) != 2:
            print("Usage: mv <source> <destination>")
            return
        
        source, dest = parts
        
        # Resolve source path
        sourceCluster, sourceFile = self._resolvePath(source)
        if sourceCluster is None or sourceFile is None:
            print(f"Source path invalid: {source}")
            return
        
        # Resolve destination path
        destCluster, destFile = self._resolvePath(dest)
        if destCluster is None or destFile is None:
            print(f"Destination path invalid: {dest}")
            return
        
        if self.fileSystem.moveFile(sourceCluster, sourceFile, destCluster, destFile):
            print(f"Moved {source} to {dest}")

    def mkdir(self, dirName):
        """Create a new directory."""
        dirName = dirName.strip()
        if not dirName:
            print("Usage: mkdir <directory_name>")
            return
        
        if self.fileSystem.createDirectory(self.currentCluster, dirName):
            print(f"Created directory: {dirName}")

    def rmdir(self, dirName):
        """Remove an empty directory."""
        dirName = dirName.strip()
        if not dirName:
            print("Usage: rmdir <directory_name>")
            return
        
        if self.fileSystem.deleteDirectory(self.currentCluster, dirName):
            print(f"Removed directory: {dirName}")

    def rm(self, fileName):
        """Delete a file."""
        fileName = fileName.strip()
        if not fileName:
            print("Usage: rm <file_name>")
            return
        
        if self.fileSystem.deleteFile(self.currentCluster, fileName):
            print(f"Deleted file: {fileName}")

    def touch(self, fileName):
        """Create a new empty file."""
        fileName = fileName.strip()
        if not fileName or '.' not in fileName:
            print("Usage: touch <file_name.EXT>")
            return
        
        if self.fileSystem.createFile(self.currentCluster, fileName):
            print(f"Created file: {fileName}")

    def cat(self, fileName):
        """Display the contents of a file."""
        fileName = fileName.strip()
        if not fileName or '.' not in fileName:
            print("Usage: cat <file_name.EXT>")
            return
        
        content = self.fileSystem.readFile(self.currentCluster, fileName)
        if content:
            print(content)
        else:
            print(f"File not found or empty: {fileName}")

    def echo(self, args):
        """Write text to a file. Usage: echo <text> > <file> or echo <text> >> <file> (append)"""
        # Check for append operator first
        append_mode = False
        if ">>" in args:
            append_mode = True
            parts = args.split(">>", 1)
        elif ">" in args:
            parts = args.split(">", 1)
        else:
            # No redirect, just print
            parts = args.split()
            if len(parts) < 1:
                print("Usage: echo <text> > <file>")
            print(args)
            return
        
        if len(parts) < 2:
            print("Usage: echo <text> > <file>")
            return
        
        text = parts[0].strip()
        fileName = parts[1].strip()
        
        if not fileName:
            print("Usage: echo <text> > <file>")
            return
        
        # Resolve the file path
        fileCluster, actualFileName = self._resolvePath(fileName)
        if fileCluster is None or actualFileName is None:
            print(f"Invalid file path: {fileName}")
            return
        
        # Check if file exists
        de = self.directory.findDirectoryEntry(fileCluster, actualFileName)
        if not de:
            # Create new file
            self.fileSystem.createFile(fileCluster, actualFileName)
            self.fileSystem.writeFile(fileCluster, actualFileName, text)
        elif append_mode:
            # Append to existing file
            existing_content = self.fileSystem.readFile(fileCluster, actualFileName)
            if existing_content:
                new_content = existing_content + "\n" + text
            else:
                new_content = text
            self.fileSystem.writeFile(fileCluster, actualFileName, new_content)
        else:
            # Overwrite existing file
            self.fileSystem.writeFile(fileCluster, actualFileName, text)
        
        mode_str = "Appended to" if append_mode else "wrote to"
        print(f"{mode_str} file: {fileName}")

    def rename(self, args):
        """Rename a file or directory."""
        parts = args.split()
        if len(parts) != 2:
            print("Usage: rename <old_name> <new_name>")
            return
        
        oldName, newName = parts
        if self.fileSystem.renameEntry(self.currentCluster, oldName, newName):
            print(f"Renamed {oldName} to {newName}")

    def _resolvePath(self, path):
            """Resolve a path to a cluster and filename.
            Returns (clusterNumber, fileName) or (None, None) if path is invalid.
            Handles formats like 'filename', './dirname/filename', 'dirname/filename'
            """
            path = path.strip()
            
            # Simple filename - use current directory
            if '/' not in path:
                return (self.currentCluster, path)
            
            # Parse path
            parts = path.split('/')
            parts = [p for p in parts if p and p != '.']  # Remove empty and '.'
            
            if not parts:
                return (None, None)
            
            # Navigate to parent directory
            currentCluster = self.currentCluster
            for dirName in parts[:-1]:
                de = self.directory.findDirectoryEntry(currentCluster, dirName)
                if not de or de.attr != 0x01:
                    return (None, None)
                currentCluster = de.firstCluster
            
            # Last part is the filename
            fileName = parts[-1]
            return (currentCluster, fileName)

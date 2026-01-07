from virtual_disk import VirtualDisk
from SuperBlockManager import SuperBlockManager
from FATManager import FATManager
from Directory import Directory
from FileSystem import FileSystem
from Shell import Shell


if __name__ == "__main__":
    import os
    

    disk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "virtual_disk.bin"))
    disk = VirtualDisk()

    try:
        disk.initialize(disk_path, create_if_missing=True)
        
        # Initialize all managers
        sb = SuperBlockManager(disk)
        fat = FATManager(disk)
        directory = Directory(disk, fat)
        fileSystem = FileSystem(disk, fat, directory)
        
        # Create and run shell
        shell = Shell(fileSystem, directory)
        shell.run()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        disk.close()

from virtual_disk import VirtualDisk


if __name__ == "__main__":
    import os

    disk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "virtual_disk.bin"))
    disk = VirtualDisk()

    try:
        ''' TODO: Test the virtual disk then clean the main file it will not be used here at the end'''

    except Exception as e:
        print(f"Error: {e}")


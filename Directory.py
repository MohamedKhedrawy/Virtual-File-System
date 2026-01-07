from FATManager import FATManager 
from virtual_disk import VirtualDisk
from FsConstants import FsConstants
import re

class DirectoryEntry:
    def __init__(self, name, attr, firstCluster=5, fileSize=0):
        self.name = name
        self.attr = attr
        self.firstCluster = firstCluster
        self.fileSize = fileSize
    
    @staticmethod
    def directoryEntryToBytes(entry):
        # Format name to 8.3 and pad to 11 bytes (no dot)
        name = Directory.formatNameTo8Dot3(entry.name).replace('.', '')
        name_bytes = name.encode('ascii').ljust(11, b' ')
        attr_byte = bytes([entry.attr])
        first_cluster_bytes = entry.firstCluster.to_bytes(2, 'little')
        file_size_bytes = entry.fileSize.to_bytes(4, 'little')
        rest = b'\x00' * (Directory.ENTRY_SIZE - (11 + 1 + 2 + 4))
        return name_bytes + attr_byte + first_cluster_bytes + file_size_bytes + rest
    
    @staticmethod
    def bytesToDirectoryEntry(data):
        # Read 11 bytes: 8 for base name, 3 for extension
        rawName = data[0:11].decode('ascii')
        baseName = rawName[0:8]  # First 8 chars (with padding)
        ext = rawName[8:11]      # Last 3 chars (with padding)
        # Only include extension if it's not all spaces
        if ext.strip():
            name = baseName.rstrip() + "." + ext.rstrip()
        else:
            name = baseName.rstrip()
        attr = data[11]
        firstCluster = int.from_bytes(data[12:14], 'little')
        fileSize = int.from_bytes(data[14:18], 'little')
        return DirectoryEntry(name, attr, firstCluster, fileSize)


class Directory:
    ENTRY_SIZE = 32
    
    def __init__(self, disk, fat):
        self.disk = disk
        self.fat = fat
        self.entries = []

    def readDirectoryEntry(self, clusterNumber):
        # get the directory cluster chain
        result = []
        chain = self.fat.followChain(clusterNumber)
        # read every cluster and divide into entries
        for cluster in chain: 
            clusterData = self.disk.read_cluster(cluster)
            clusterEntries = FsConstants.CLUSTER_SIZE // Directory.ENTRY_SIZE
            # read every entry and append to the result array
            for i in range(clusterEntries):
                entryData = clusterData[i * Directory.ENTRY_SIZE:(i + 1) * Directory.ENTRY_SIZE]
                if entryData[0] == 0x00:
                    continue  # Unused entry
                de = DirectoryEntry.bytesToDirectoryEntry(entryData)
                result.append(de)
        return result

    def findDirectoryEntry(self, clusterNumber, entryName):
        # Normalize the target name for comparison (8.3 format without padding)
        formatted = Directory.formatNameTo8Dot3(entryName)
        # Strip the padded format to match bytesToDirectoryEntry output
        baseName, ext = formatted.split('.') if '.' in formatted else (formatted, '')
        targetName = baseName.rstrip() + ("." + ext.rstrip() if ext.strip() else "")
        chain = self.fat.followChain(clusterNumber)
        #read every cluster and divide into entries
        for cluster in chain:
            clusterData = self.disk.read_cluster(cluster)
            # read every entry and compare against target
            for i in range(FsConstants.CLUSTER_SIZE // Directory.ENTRY_SIZE):
                entryData = clusterData[i * Directory.ENTRY_SIZE:(i + 1) * Directory.ENTRY_SIZE]
                if entryData[0] == 0x00:
                    continue  # Unused entry
                de = DirectoryEntry.bytesToDirectoryEntry(entryData)
                if de.name == targetName:
                    return de
        # No results
        return None

    def addDirectoryEntry(self, clusterNumber, entry):
        #follow chain searching for an empty entry slot
        chain = self.fat.followChain(clusterNumber)
        for cluster in chain:
            clusterData = bytearray(self.disk.read_cluster(cluster))
            for i in range(FsConstants.CLUSTER_SIZE // Directory.ENTRY_SIZE):
                entryData = clusterData[i * Directory.ENTRY_SIZE:(i + 1) * Directory.ENTRY_SIZE]
                if entryData[0] == 0x00:
                    # Found an empty entry slot
                    entryBytes = DirectoryEntry.directoryEntryToBytes(entry)
                    clusterData[i * Directory.ENTRY_SIZE:(i + 1) * Directory.ENTRY_SIZE] = entryBytes
                    self.disk.write_cluster(cluster, bytes(clusterData))
                    return
        #if no slots found, allocate new cluster and recurse on the add function
        newCluster = self.fat.addClustersToChain(clusterNumber, 1)
        self.addDirectoryEntry(newCluster, entry)

    def removeDirectoryEntry(self, clusterNumber, entryName):
        #find the needed directory and normalize name for comparison
        formatted = Directory.formatNameTo8Dot3(entryName)
        baseName, ext = formatted.split('.') if '.' in formatted else (formatted, '')
        targetName = baseName.rstrip() + ("." + ext.rstrip() if ext.strip() else "")
        chain = self.fat.followChain(clusterNumber)
        for cluster in chain:
            clusterData = bytearray(self.disk.read_cluster(cluster))
            for i in range(FsConstants.CLUSTER_SIZE // Directory.ENTRY_SIZE):
                entryData = clusterData[i * Directory.ENTRY_SIZE:(i + 1) * Directory.ENTRY_SIZE]
                if entryData[0] != 0x00:
                    de = DirectoryEntry.bytesToDirectoryEntry(bytes(entryData))
                    if de.name == targetName:
                        # Mark as deleted by zeroing first byte
                        clusterData[i * Directory.ENTRY_SIZE] = 0x00
                        #flush changes to disk
                        self.disk.write_cluster(cluster, bytes(clusterData))
                        return True
        return False

    @staticmethod
    def formatNameTo8Dot3(name):
        """Convert name to 8.3 format."""
        baseName, ext = name.split('.') if '.' in name else (name, '')
        baseName = baseName.upper()
        ext = ext.upper()
        baseName = re.sub(r'[^A-Z0-9]', '', baseName)
        ext = re.sub(r'[^A-Z0-9]', '', ext)
        baseName = baseName[:8]
        ext = ext[:3]
        baseName = baseName.ljust(8)
        # Only add dot and pad extension if extension exists
        if ext:
            ext = ext.ljust(3)
            return baseName + "." + ext
        else:
            return baseName

    @staticmethod
    def parse8Dot3Name(rawName):
        """Convert 8.3 internal format to readable name"""
        if '.' in rawName:
            baseName, ext = rawName.split('.', 1)
            baseName = baseName.rstrip()
            ext = ext.rstrip()
            if ext:
                return baseName + "." + ext
            return baseName
        return rawName.rstrip()

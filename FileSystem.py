from Directory import DirectoryEntry, Directory
from FsConstants import FsConstants


class FileSystem:
    def __init__(self, disk, fatManager, directory):
        self.disk = disk
        self.fat = fatManager
        self.directory = directory

    def createFile(self, parentCluster, fileName):
        """Create a new file in the specified parent directory."""
        # Search for duplicates
        de = self.directory.findDirectoryEntry(parentCluster, fileName)
        if de:
            print("A file with that name already exists")
            return False
        
        # Allocate a cluster for the new file
        newCluster = self.fat.allocateChain(1)
        # Add file entry
        de = DirectoryEntry(fileName, 0x00, newCluster, 0)  # 0x00 = file attribute
        self.directory.addDirectoryEntry(parentCluster, de)
        #flush to disk
        self.fat.flushFatToDisk()
        return True

    def writeFile(self, parentCluster, fileName, data):
        """Write data to an existing file."""
        de = self.directory.findDirectoryEntry(parentCluster, fileName)
        if not de:
            print("File not found")
            return False
        
        # Convert data to bytes
        dataBytes = data.encode('utf-8') if isinstance(data, str) else data
        
        # Calculate clusters needed (minimum 1)
        clustersNeeded = max(1, (len(dataBytes) + FsConstants.CLUSTER_SIZE - 1) // FsConstants.CLUSTER_SIZE)
        
        # Free old chain and allocate new one
        self.fat.freeChain(de.firstCluster)
        newFirst = self.fat.allocateChain(clustersNeeded)
        
        # Write data to clusters
        chain = self.fat.followChain(newFirst)
        for i, cluster in enumerate(chain):
            start = i * FsConstants.CLUSTER_SIZE
            end = start + FsConstants.CLUSTER_SIZE
            chunk = dataBytes[start:end]
            self.disk.write_cluster(cluster, chunk)
        
        # Update directory entry with new cluster and size (remove and reenter)
        self.directory.removeDirectoryEntry(parentCluster, fileName)
        updatedEntry = DirectoryEntry(fileName, de.attr, newFirst, len(dataBytes))
        self.directory.addDirectoryEntry(parentCluster, updatedEntry)
        self.fat.flushFatToDisk()
        return True

    def readFile(self, parentCluster, fileName):
        """Read and return the contents of a file."""
        de = self.directory.findDirectoryEntry(parentCluster, fileName)
        if not de:
            print("File not found")
            return None
        
        # Follow cluster chain and read data
        chain = self.fat.followChain(de.firstCluster)
        data = b''
        for cluster in chain:
            data += self.disk.read_cluster(cluster)
        
        # Trim to actual file size and decode
        return data[:de.fileSize].decode('utf-8', errors='ignore')

    def deleteFile(self, parentCluster, fileName):
        """Delete a file from the specified directory."""
        de = self.directory.findDirectoryEntry(parentCluster, fileName)
        if not de:
            print("File not found")
            return False
        
        # Check that it's a file, not a directory
        if de.attr == 0x01:
            print("Cannot delete directory with rm. Use rmdir.")
            return False
        #free resources (chain and directory)
        self.fat.freeChain(de.firstCluster)
        self.directory.removeDirectoryEntry(parentCluster, fileName)
        self.fat.flushFatToDisk()
        return True

    def renameEntry(self, directoryCluster, oldName, newName):
        """Rename a file or directory."""
        # Check if new name already exists
        existing = self.directory.findDirectoryEntry(directoryCluster, newName)
        if existing:
            print("A file with that name already exists")
            return False
        
        # Find the entry to rename
        de = self.directory.findDirectoryEntry(directoryCluster, oldName)
        if not de:
            print("File not found")
            return False
        
        # Remove old entry and add with new name
        self.directory.removeDirectoryEntry(directoryCluster, oldName)
        renamedEntry = DirectoryEntry(newName, de.attr, de.firstCluster, de.fileSize)
        self.directory.addDirectoryEntry(directoryCluster, renamedEntry)
        self.fat.flushFatToDisk()
        return True

    def copyFile(self, sourceCluster, sourceName, destCluster, destName):
        """Copy a file to a destination."""
        # Read source file
        de = self.directory.findDirectoryEntry(sourceCluster, sourceName)
        if not de:
            print("Source file not found")
            return False
        
        # Check if source is a file, not a directory
        if de.attr != 0x00:
            print("Cannot copy a directory. Use a file.")
            return False
        
        # Check if destination exists
        if self.directory.findDirectoryEntry(destCluster, destName):
            print("Destination file already exists")
            return False
        
        # Read source data
        chain = self.fat.followChain(de.firstCluster)
        data = b''
        for cluster in chain:
            data += self.disk.read_cluster(cluster)
        data = data[:de.fileSize]
        
        # Calculate clusters needed
        clustersNeeded = max(1, (len(data) + FsConstants.CLUSTER_SIZE - 1) // FsConstants.CLUSTER_SIZE)
        
        # Allocate clusters for destination
        newCluster = self.fat.allocateChain(clustersNeeded)
        
        # Write data to clusters
        for i, cluster in enumerate(self.fat.followChain(newCluster)):
            start = i * FsConstants.CLUSTER_SIZE
            end = start + FsConstants.CLUSTER_SIZE
            chunk = data[start:end]
            self.disk.write_cluster(cluster, chunk)
        
        # Create destination entry directly
        destEntry = DirectoryEntry(destName, 0x00, newCluster, len(data))
        self.directory.addDirectoryEntry(destCluster, destEntry)
        self.fat.flushFatToDisk()
        return True

    def moveFile(self, sourceCluster, sourceName, destCluster, destName):
        """Move a file to a destination (copy then delete source)."""
        if self.copyFile(sourceCluster, sourceName, destCluster, destName):
            return self.deleteFile(sourceCluster, sourceName)
        return False

    def createDirectory(self, parentCluster, dirName):
        """Create a new directory."""
        de = self.directory.findDirectoryEntry(parentCluster, dirName)
        if de:
            print("Directory already exists")
            return False
        
        # Allocate a cluster for the new directory
        newCluster = self.fat.allocateChain(1)
        de = DirectoryEntry(dirName, 0x01, newCluster, 0)
        self.directory.addDirectoryEntry(parentCluster, de)
        
        self.fat.flushFatToDisk()
        return True

    def deleteDirectory(self, parentCluster, dirName):
        """Delete an empty directory."""
        de = self.directory.findDirectoryEntry(parentCluster, dirName)
        if not de:
            print("Directory not found")
            return False
        
        # Check that it's a directory
        if de.attr != 0x01:
            print("Not a directory. Use rm for files.")
            return False
        
        # Check if directory is empty
        entries = self.directory.readDirectoryEntry(de.firstCluster)
        if entries:
            print("Directory not empty")
            return False
        
        self.fat.freeChain(de.firstCluster)
        self.directory.removeDirectoryEntry(parentCluster, dirName)
        self.fat.flushFatToDisk()
        return True

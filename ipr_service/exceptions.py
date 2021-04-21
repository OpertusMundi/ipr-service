class DBItemNotFound(Exception):
    """Raised when an item not found on update."""

class NotRasterError(Exception):
    """Raised when a directory is expected to but does not contain a raster."""

class NotVectorError(Exception):
    """Raised when a directory is expected to but does not contain a vector."""

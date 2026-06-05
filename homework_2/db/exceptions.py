'''
Custom exceptions for the Document domain.

A single base (DocumentError) lets callers catch the whole domain, while the
specific subclasses carry the offending value for clear, human-readable messages.
'''


class DocumentError(Exception):
    '''Base for all errors in the Document domain.'''


class DocumentNotFoundError(DocumentError):
    '''Raised when a document id does not exist in the database.'''

    def __init__(self, doc_id: int) -> None:
        super().__init__(f"Document with id={doc_id} not found")
        self.doc_id = doc_id


class DuplicateDocumentError(DocumentError):
    '''Raised when a document with the same filename already exists.'''

    def __init__(self, filename: str) -> None:
        super().__init__(f"Document with filename='{filename}' already exists")
        self.filename = filename


class InvalidMetadataError(DocumentError):
    '''Raised when the metadata payload is not a valid dict.'''

    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid metadata: {reason}")
        self.reason = reason

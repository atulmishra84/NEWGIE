class KnowledgeError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class NotFoundError(KnowledgeError):
    def __init__(self, message: str):
        super().__init__("not_found", message, retryable=False)


class ConflictError(KnowledgeError):
    def __init__(self, message: str):
        super().__init__("conflict", message, retryable=False)


class ValidationError(KnowledgeError):
    def __init__(self, message: str):
        super().__init__("validation_error", message, retryable=False)

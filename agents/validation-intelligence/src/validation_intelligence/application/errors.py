class ValidationError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class NotFoundError(ValidationError):
    def __init__(self, message: str):
        super().__init__("not_found", message)

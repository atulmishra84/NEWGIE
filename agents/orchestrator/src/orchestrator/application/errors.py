class OrchestratorError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

class NotFoundError(OrchestratorError):
    def __init__(self, message: str):
        super().__init__("not_found", message)

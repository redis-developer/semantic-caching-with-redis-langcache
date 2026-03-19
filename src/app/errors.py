class ClientError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status

class DomainError(Exception):
    """Error base del dominio."""


class InvalidPayloadError(DomainError):
    pass


class JobNotFoundError(DomainError):
    pass


class ExternalServiceError(DomainError):
    """Una API externa respondió con error o no está disponible."""

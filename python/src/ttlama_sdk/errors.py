"""Exceptions raised by the TTL-LAMa Python SDK."""


class TTLamaError(Exception):
    """Base exception for SDK errors."""


class APIError(TTLamaError):
    """An HTTP or transport error returned while accessing the API.
    
    :param message: Error message.
    :type message: str
    :param status_code: HTTP status code, if available.
    :type status_code: int | None
    :param lease_id: Lease ID related to the error, if available.
    :type lease_id: int | None
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        lease_id: int | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.lease_id = lease_id


class AuthenticationError(APIError):
    """Authentication failed or the session expired."""


class AuthorizationError(APIError):
    """The authenticated user lacks the required permissions."""


class ValidationError(APIError):
    """The request or its CSRF token is invalid."""


class NotFoundError(APIError):
    """The requested resource was not found."""


class ConflictError(APIError):
    """The request conflicts with the current resource state."""


class ProvisioningError(APIError):
    """VPN provisioning could not be confirmed."""

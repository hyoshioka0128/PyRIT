# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from abc import ABC
import logging
import json

from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type, after_log
from openai import RateLimitError
from typing import Callable

from pyrit.common.constants import RETRY_WAIT_MIN_SECONDS, RETRY_WAIT_MAX_SECONDS, RETRY_MAX_NUM_ATTEMPTS

logger = logging.getLogger(__name__)


class PyritException(Exception, ABC):

    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Status Code: {status_code}, Message: {message}")

    def process_exception(self) -> str:
        """
        Logs and returns a string representation of the exception.
        """
        log_message = f"{self.__class__.__name__} encountered: Status Code: {self.status_code}, Message: {self.message}"
        logger.error(log_message)
        # Return a string representation of the exception so users can extract and parse
        return json.dumps({"status_code": self.status_code, "message": self.message})


class BadRequestException(PyritException):
    """Exception class for bad client requests."""

    def __init__(self, status_code: int = 400, *, message: str = "Bad Request"):
        super().__init__(status_code, message)


class RateLimitException(PyritException):
    """Exception class for authentication errors."""

    def __init__(self, status_code: int = 429, *, message: str = "Rate Limit Exception"):
        super().__init__(status_code, message)


class EmptyResponseException(BadRequestException):
    """Exception class for empty response errors."""

    def __init__(self, status_code: int = 204, *, message: str = "No Content"):
        super().__init__(status_code=status_code, message=message)


def pyrit_retry(func: Callable) -> Callable:
    """
    A decorator to apply retry logic with exponential backoff to a function.

    Retries the function if it raises RateLimitError or EmptyResponseException,
    with a wait time between retries that follows an exponential backoff strategy.
    Logs retry attempts at the INFO level and stops after a maximum number of attempts.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The decorated function with retry logic applied.
    """
    return retry(
        reraise=True,
        retry=retry_if_exception_type(RateLimitError) | retry_if_exception_type(EmptyResponseException),
        wait=wait_random_exponential(min=RETRY_WAIT_MIN_SECONDS, max=RETRY_WAIT_MAX_SECONDS),
        after=after_log(logger, logging.INFO),
        stop=stop_after_attempt(RETRY_MAX_NUM_ATTEMPTS),
    )(func)

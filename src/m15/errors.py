class M15Error(Exception):
    pass


class CandleValidationError(M15Error, ValueError):
    pass


class CandleFormatError(M15Error, ValueError):
    pass


class InsufficientDataError(M15Error, ValueError):
    pass

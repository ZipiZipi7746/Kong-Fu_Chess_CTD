# TODO(design): Both domain exceptions subclass the built-in ValueError
# directly, and main.py's run() catches board-parsing failures with a
# bare "except ValueError" - which would also silently swallow an
# unrelated ValueError raised by a bug elsewhere in the call chain (e.g.
# int(parts[1]) in commands.parse_command). Introducing a small
# exception hierarchy rooted in a project-specific base (e.g.
# GameInputError, with BoardParsingError/CommandParsingError as
# subclasses covering these two and any future parsing failures) would
# let callers catch exactly the expected domain failures and let
# anything else propagate (Fail Fast, explicit error contracts, clearer
# Separation of Concerns between "expected bad input" and "a bug").
# Not changed now: today's two exceptions and one catch site behave
# correctly, and this would be a type change with no behavior
# difference for the current test suite - not required by anything the
# project needs yet.
class UnknownToken(ValueError):
    pass


class RowWidthMismatch(ValueError):
    pass

"""Everything this package raises, in one place.

One module so a caller can see the whole set at once, and so `except` has
somewhere to import from. It imports nothing from the rest of the package, which
is what keeps it from ever closing a cycle: everything here raises, so everything
here imports this, and an import running the other way would make the order
modules happen to load in decide whether the package works at all.
"""

from __future__ import annotations


class NoHeader(Exception):
    """No region of the image scored well enough to be a header.

    Raised rather than returned because there is no useful partial answer. A
    caller that cannot find a header cannot ask which layout the image uses, and
    a sentinel would be checked once and then carried into arithmetic.
    """


class NotWholeBanks(Exception):
    """The image holds part of a bank.

    Every layout here is described in banks, so a size that is not a whole
    number of them has no layout. This is a property of the file rather than of
    the request, which is why it is refused where the size is read.
    """


class NeedsBankCount(Exception):
    """The layout cannot be resolved without knowing how many banks there are.

    One layout maps its last region differently depending on the size of the
    image, so resolving an address in it is not a question about the address
    alone. The message names the call that supplies the missing number.
    """


class UnknownModelError(Exception):
    """No layout goes by that name, under any spelling this package accepts.

    The same name the other members use for the same refusal, so a caller
    handling it across packages writes one `except` rather than one per part.
    """

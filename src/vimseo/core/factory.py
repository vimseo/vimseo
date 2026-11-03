# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from gemseo.core.base_factory import BaseFactory


def get_class(
    factory: BaseFactory,
    class_name: str,
    kind: str,
    hint: str = "",
    available_names: Iterable[str] | None = None,
) -> type:
    """Return a class of a factory, or explain why it is not available.

    Args:
        factory: The factory.
        class_name: The name of the class.
        kind: The kind of class, e.g. ``"model"``, used in the error message.
        hint: How the class must be declared to be found by the factory.
        available_names: The names of the available classes to list in the error
            message. If ``None``, all the classes of the factory.

    Returns:
        The class.

    Raises:
        ImportError: When the class is not available.
    """
    try:
        return factory.get_class(class_name)
    except ImportError:
        pass

    if available_names is None:
        available_names = factory.class_names
    message = [f"The {kind} {class_name} is not available."]
    if hint:
        message.append(hint)
    message.append(f"The available ones are: {', '.join(available_names)}.")
    # GEMSEO ignores the modules that fail to import, and so the classes they define.
    if factory.failed_imports:
        failed_imports = "; ".join(
            f"{module_name}: {str(error)[:200]}"
            for module_name, error in factory.failed_imports.items()
        )
        message.append(
            "These modules could not be imported, so the classes they define are not "
            f"available: {failed_imports}."
        )
    raise ImportError(" ".join(message))


def create_instance(
    cls: type, kind: str, expected_signature: str, *args: Any, **kwargs: Any
) -> Any:
    """Create an instance of a class, explaining a constructor not accepting the
    arguments.

    Args:
        cls: The class.
        kind: The kind of class, e.g. ``"model"``, used in the error message.
        expected_signature: An example of a valid constructor, for the error message.
        *args: The positional arguments of the constructor.
        **kwargs: The keyword arguments of the constructor.

    Returns:
        The instance.

    Raises:
        TypeError: When the instance cannot be created, e.g. because a constructor
            does not accept the arguments.
    """
    try:
        return cls(*args, **kwargs)
    except TypeError as error:
        message = (
            f"The {kind} {cls.__name__} cannot be created with the positional "
            f"arguments {list(args)} and the keyword arguments {sorted(kwargs)}: "
            f"{error}. Check that its constructor, and the ones it calls, accept "
            f"them, e.g. {expected_signature}."
        )
        raise TypeError(message) from error

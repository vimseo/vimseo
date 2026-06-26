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

from dataclasses import dataclass

from docstring_inheritance import GoogleDocstringInheritanceMeta
from strenum import StrEnum


class LoadDirectionLiteral(StrEnum):
    LL = "LL"  # longitudinal
    TT = "TT"  # transverse
    ZZ = "ZZ"  # out-of-plane
    LT = "LT"  # shear_LT
    LZ = "LZ"  # shear_LZ
    TZ = "TZ"  # shear_TZ


class LoadDirectionNumbered(StrEnum):
    C11 = "11"
    C22 = "22"
    C33 = "33"
    C12 = "12"
    C13 = "13"
    C23 = "23"


class LoadSign(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class LoadType(StrEnum):
    STRESS = "stress"
    STRAIN = "strain"


@dataclass
class Load(metaclass=GoogleDocstringInheritanceMeta):
    """The load of a load case."""

    direction: LoadDirectionLiteral = ""
    sign: LoadSign = ""
    type: LoadType = ""

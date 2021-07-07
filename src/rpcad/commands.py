#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import enum


class Command:
    def __init__(self, name: str, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs


class PhysicalProperty(enum.Enum):
    # get mass in kg
    Mass = enum.auto()

    # get area in m^2
    Area = enum.auto()

    # get volume in m^3
    Volume = enum.auto()

    # get density in kg / m^3
    Density = enum.auto()

    # get bounding box [min, max] in m
    BoundingBox = enum.auto()

    # get center of mass in m
    CenterOfMass = enum.auto()


class Accuracy(enum.Enum):
    Low = enum.auto()
    Medium = enum.auto()
    High = enum.auto()
    VeryHigh = enum.auto()

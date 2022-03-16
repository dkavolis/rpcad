#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from __future__ import annotations


class Parameter:
    def __init__(self, value: float, expression: str) -> None:
        self.value = value
        self.expression = expression

    def __str__(self) -> str:
        return f"{self.value} ({self.expression})"

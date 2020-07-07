#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 06-Jun-2020
@Filename:             parameter.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   06-Jun-2020
"""


class Parameter:
    def __init__(self, value: float, expression: str) -> None:
        self.value = value
        self.expression = expression

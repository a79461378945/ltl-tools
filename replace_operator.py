# -*- coding:utf-8 -*-

import os
import sys
import subprocess
import queue
import json
from copy import deepcopy
import argparse
from ltlf2dfa.parser.ltlf import LTLfParser, LTLfAnd, LTLfUntil, LTLfNot, LTLfAlways, LTLfAtomic, LTLfNext, LTLfOr, LTLfEventually, LTLfImplies, LTLfRelease, LTLfEquivalence

import signal

# - [ ] 输入一般LTL公式，转化为一个等价的封闭算子集合的LTL公式。
#     - 一般公式算子集：{0,1,!,&,|,X,F,G,U,W,R, ->}
#     - 封闭算子集合：{0,1,!,&,X,U}
#
#  1.由于ltlf2dfa不支持W，所以这里用了<->代替W
#


# 将输入的原始ltl公式转换成 只有 0,1,!,&,X,U 的
# 需要转换的有 |,F,G,W(用了<->代替),R

# a|b  ===  !(!a & !b)
# F a === 1 U a
# G a === 0 R a === !(1 U !a)
# a R b === !(!a U !b)
# a W b === (a U b) | G(a)  //这里w是用了<-> LTLfEquivalence
# a -> b === !a | b === !(a & !b)

def transform_ltl(f):
    #无需转换的部分
    if isinstance(f, LTLfAtomic):
        return f.s
    if isinstance(f, LTLfAnd) or isinstance(f, LTLfUntil) : #or isinstance(f, LTLfOr) or isinstance(f, LTLfRelease) or isinstance(f, LTLfImplies)
        if len(f.formulas)>2: #多个&起来的，后面就变成一个nf
            nf=deepcopy(f)
            nf.formulas=deepcopy(nf.formulas[1:])
            f.formulas[1]=nf
        return '('+transform_ltl(f.formulas[0])+')'+f.operator_symbol+'('+transform_ltl(f.formulas[1])+')'
    if isinstance(f, LTLfNot) or isinstance(f, LTLfNext): # or isinstance(f, LTLfAlways) or isinstance(f, LTLfEventually)
        return f.operator_symbol+'('+transform_ltl(f.f)+')'

    #需要转换的运算符
    if isinstance(f,LTLfOr): # a|b  ===  !(!a & !b)
        if len(f.formulas)>2: #多个&起来的，后面就变成一个nf
            nf=deepcopy(f)
            nf.formulas=deepcopy(nf.formulas[1:])
            f.formulas[1]=nf
        return '!(!(' + transform_ltl(f.formulas[0]) + ')&!(' + transform_ltl(f.formulas[1]) + '))'
    if isinstance(f,LTLfEventually):# F a === 1 U a
        return '(1)U('+transform_ltl(f.f)+')'
    if isinstance(f,LTLfAlways):# G a === 0 R a === !(1 U !a)
        return "!((1) U !("+transform_ltl(f.f)+'))'
    if isinstance(f,LTLfRelease):# a R b === !(!(a) U !(b))
        return '!(!('+transform_ltl(f.formulas[0])+')U!('+transform_ltl(f.formulas[1])+'))'
    if isinstance(f,LTLfEquivalence): #a W b === (a U b) | G(a)  //这里w是用了<-> LTLfEquivalence
        nf_l=LTLfUntil(f.formulas)
        nf_r=LTLfAlways(f.formulas[0])
        nf=LTLfOr([nf_l,nf_r])
        return transform_ltl(nf)
    if isinstance(f,LTLfImplies): # a -> b === !a | b === !(a & !b)
        return "!((%s) & !(%s))"%(transform_ltl(f.formulas[0]), transform_ltl(f.formulas[1]))
    assert 0



#
def ltl2simpleltl(ltl: str):
    parser = LTLfParser()
    formula = parser(ltl.replace('1', 'true').replace('0', 'false').replace('W','<->'))
    return transform_ltl(formula).replace('true', '1').replace('false', '0').replace('<->', 'W')



if __name__ == "__main__":

    test_cases=['a W b','F(a)','G(a)','a | b','a R b','a -> b']
    for case in test_cases:
        print(case,' is converted to  ',ltl2simpleltl(case))

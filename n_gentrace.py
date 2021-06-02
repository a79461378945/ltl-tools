# -*- coding:utf-8 -*-
import os
import sys
import subprocess
import queue
import json
from copy import deepcopy
import time
import timeout_decorator
import argparse
from ltlf2dfa.parser.ltlf import LTLfParser, LTLfAnd, LTLfUntil, LTLfNot, LTLfAlways, LTLfAtomic, LTLfNext, LTLfOr, LTLfEventually, LTLfImplies, LTLfRelease
from ltl_model_check import check
import signal

TIME_LIMIT=60

class LTL():

    def __init__(self, vocab, formulae, assumption, smv_file):
        self.vocab = vocab
        self.formulae = formulae
        self.assumption = assumption
        self.smv_file = smv_file
        self.cache = {}

    def printinfo(self):
        print('Formulae: ', self.formulae)
        print('Assumption: ', self.assumption)

    def _LTL2SMV(self):
        content = "MODULE main\nVAR\n"
        for v in self.vocab:
            content += v + ':boolean;\n'

        content += 'LTLSPEC!(\n'
        for i in range(len(self.formulae)):
            if i is 0:
                content += '( ' + self.formulae[i] + ' )\n'
            else:
                content += '& ( ' + self.formulae[i] + ' )\n'
        for i in range(len(self.assumption)):
            content += '& ( ' + self.assumption[i] + ' )\n'
        content += ')'

        with open(self.smv_file, 'w') as smvfile:
            smvfile.write(content)

    @timeout_decorator.timeout(TIME_LIMIT)
    def isSAT(self):

        self._LTL2SMV()

        if (not os.path.exists(self.smv_file)):
            print('Cannot find SMV file.')
            sys.exit(1)

        cmd='./lib/nuXmv-2.0.0-Linux' + ' ' + self.smv_file
        # result = os.popen('./lib/nuXmv-2.0.0-Linux' + ' ' + self.smv_file)
        # # print (result.read())
        # result = result.readlines()


        self.mytask = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        errstr = self.mytask.stderr.read()
        result = self.mytask.stdout.readlines()

        for i in range(len(result)):
            result[i]=result[i].decode()


        # print(result)
        SAT = False
        traces = []

        # print('result\n',result)
        for line in result:
            if (line.find('specification') != -1):
                # print(line)
                if (line.find('is false') != -1):
                    SAT = True
                break
        # if len(errstr)!=0:
        #     # print('err!!!\n',errstr)
        #     SAT=False
        # !()is UNSAT then () is SAT
        loop_start = 0
        if (SAT):
            # print("SAT")
            true_vars = set()
            false_vars = set()
            loop_start=0
            for i in range(27, len(result)):
                if (result[i].find('Loop') != -1):
                    loop_start=len(traces)
                if (result[i].find("->") != -1):
                    trace = []
                    j = i + 1
                    while (j < len(result) and result[j].find("->") == -1):
                        action = result[j].replace("\n", "").replace(" ", "")
                        if (action.find("TRUE") != -1):
                            if action[:action.find('=')] in false_vars:
                                false_vars.remove(action[:action.find('=')])
                            trace.append(str(action[:action.find('=')]))
                            true_vars.add(action[:action.find('=')])
                        elif (action.find("FALSE") != -1): # and action[:action.find('=')] in true_vars
                            if action[:action.find('=')] in true_vars:
                                true_vars.remove(action[:action.find('=')])
                            # trace.append('!'+action[:action.find('=')])
                            false_vars.add(action[:action.find('=')])
                        j += 1
                    # print(true_vars)
                    for true_var in true_vars:
                        if (true_var not in trace):
                            trace.append(str(true_var))
                    # for false_var in false_vars:
                    #     if ('!'+false_var not in trace):
                    #         trace.append('!'+false_var)
                    i = j
                    traces.append(trace)
        # print(traces)

        return SAT, traces, loop_start


def convert_trace(trace, loop_start):
    retstr=''
    cnt=0
    for state in trace:
        if cnt!=0:
            retstr+=';'
        if cnt==loop_start:
            retstr+='{'

        for i in range(len(state)-1):
            retstr+='&'
        for var in state:
            retstr+=var

        cnt+=1

    retstr+='}'
    return retstr

# 将输入的原始ltl公式转换成前缀公式树
def preorder_turple(f):
    if isinstance(f, LTLfAtomic):
        return f.s.replace('true', '1').replace('false', '0')
    if isinstance(f, LTLfAnd) or isinstance(f, LTLfUntil) or isinstance(f, LTLfOr) or isinstance(f, LTLfRelease) or isinstance(f, LTLfImplies):
        if len(f.formulas)>2:
            nf=deepcopy(f)
            nf.formulas=nf.formulas[1:]
            return (f.operator_symbol,preorder_turple(f.formulas[0]),preorder_turple(nf))
        return tuple([f.operator_symbol.replace('R', 'W')]+[preorder_turple(f.formulas[i]) for i in range(len(f.formulas))])
    if isinstance(f, LTLfNot) or isinstance(f, LTLfNext) or isinstance(f, LTLfAlways) or isinstance(f, LTLfEventually):
        return (f.operator_symbol,preorder_turple(f.f))

def preorder(f):
    if isinstance(f, LTLfAtomic):
        return f.s
    if isinstance(f, LTLfAnd) or isinstance(f, LTLfUntil) or isinstance(f, LTLfOr) or isinstance(f, LTLfRelease) or isinstance(f, LTLfImplies):
        result = f.operator_symbol
        if len(f.formulas)>2:
            nf=deepcopy(f)
            nf.formulas=nf.formulas[:-1]
            tstrs=[preorder(nf),preorder(f.formulas[-1])]
        else:
            tstrs = [preorder(f.formulas[0]),preorder(f.formulas[1])]
        for i in tstrs:
            result += i
        return result
    if isinstance(f, LTLfNot) or isinstance(f, LTLfNext) or isinstance(f, LTLfAlways) or isinstance(f, LTLfEventually):
        result = f.operator_symbol
        result += preorder(f.f)
        return result


def ltl2prefix(ltl: str):
    parser = LTLfParser()
    # print(ltl.replace('1', 'true').replace('0', 'false').replace('W','R'))
    formula = parser(ltl.replace('1', 'true').replace('0', 'false').replace('W','R'))
    return preorder(formula).replace('true', '1').replace('false', '0').replace('R', 'W')


# 需注意有R的要改
if __name__ == "__main__":

    #并行化完成任务，每个进程完成minidx到maxidx部分

    #python3 teachingLTL.py -t1 0 -t2 50000 -o 0.json &
    parser = argparse.ArgumentParser(description='Main script for active learning')
    parser.add_argument('-f', type=str, required=False ,default='randltls', help='input file containing ltls')
    parser.add_argument('-t1', type=int, required=True, help='min idx')
    parser.add_argument('-t2', type=int, required=True, help='max idx')
    parser.add_argument('-o', type=str, required=True, help='output file')

    args = parser.parse_args()
    infile=args.f
    minidx=args.t1
    maxidx=args.t2
    ofile=args.o
    vocab=[i for i in 'abcdefghij']
    vocab=set(vocab)

    output=[]
    f=open(infile,'r')
    timeoutcnt=0
    unsolvecnt=0
    errcnt=0

    lines=f.readlines()[minidx:maxidx]
    f.close()

    cnt=minidx-1
    for line in lines:
        cnt+=1
        if cnt<minidx:
            continue
        if cnt%100==0:
            print('\r','min',minidx,'max',maxidx,'cnt',cnt,'timeout',timeoutcnt,'unsat',unsolvecnt,'errcnt',errcnt,end='')
        if cnt>maxidx:
            break
        ltl=line
        if len(ltl.strip())==0:
            # print('skip??')
            cnt-=1
            continue
        # print('ltl:',ltl.replace('0','(a & ! a)').replace('1','(a | ! a)'))
        temp_file_name='temp/%dt%dtempfile'%(minidx,maxidx)
        a = LTL(vocab, [ltl.replace('0','(a & ! a)').replace('1','(a | ! a)')], [], temp_file_name)
        try:
            b = a.isSAT()
        except timeout_decorator.timeout_decorator.TimeoutError:
            # os.killpg(a.mytask.pid, signal.SIGUSR1)
            os.system('kill -9 `ps -ef | grep "%s" | grep -v "grep" '%temp_file_name + "| awk '{print $2}'`")
            b = (False,'timeout')
        if b[0]: # SAT
            output.append({'trace':convert_trace(b[1],b[2]),'ltl_pre':ltl2prefix(ltl),'ltl':ltl})
            if not check(ltl, output[-1]['trace'],vocab):
                output[-1]['ltl_check_res']='unsat'
                errcnt+=1
            else:
                output[-1]['ltl_check_res']='sat'
        else:
            if b[1]=='timeout':
                output.append({'ltl':ltl,'nuxmv_res':'timeout','ltl_pre':ltl2prefix(ltl)})
                timeoutcnt+=1
            else:
                output.append({'ltl': ltl, 'nuxmv_res': 'unsat','ltl_pre':ltl2prefix(ltl)})
                unsolvecnt+=1



    f.close()
    f=open(ofile,'w')
    json.dump(output,f,indent=2)
    f.close()


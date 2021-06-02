# ltl-tools
一些处理ltl公式的工具

## replace_operator

- [ ] 输入一般LTL公式，转化为一个等价的封闭算子集合的LTL公式。
    - 一般公式算子集：{0,1,!,&,|,X,F,G,U,W,R, ->}
    - 封闭算子集合：{0,1,!,&,X,U}
1.由于ltlf2dfa不支持W，所以这里用了<->代替W



使用里面的函数即可转换

```
ltl2simpleltl(ltl:str)
```



### 转换细节

其依赖的转换规则为

```
# a|b  ===  !(!a & !b)
# F a === 1 U a
# G a === 0 R a === !(1 U !a)
# a R b === !(!a U !b)
# a W b === (a U b) | G(a)  //这里w是用了<-> LTLfEquivalence
# a -> b === !a | b === !(a & !b)
```



对于&,|有多个子公式的，处理方法是将第二个和后面的所有子公式配上 &或|操作符当作第二个子公式，然后按两个子公式的情况处理



### 测试样例

```
a W b  is converted to   !(!((a)U(b))&!(!((1) U !(a))))
F(a)  is converted to   (1)U(a)
G(a)  is converted to   !((1) U !(a))
a | b  is converted to   !(!(a)&!(b))
a R b  is converted to   !(!(a)U!(b))
a -> b  is converted to   !((a) & !(b))
```

## proof_checker

The program is used to verify the output of LTSatP. 

### How to use

```
python3 proof_checker.py --trainfile LTSatP-spot-5t20-train.json --testfile LTSatP-spot-5t20-test.json --netfile res-LTSatP-spot-5t20-test.json -o LTSatP-result.json -t 40
```

--trainfile, the training data of the model. We use it to remove the test data that exists in training data. 

--testfile, the test data file. We use it to extract the test formula.

--netfile, the output file of LTSatP.

-o, name for the result file.

-t, number of threads the program uses.

## gen_onestep

### 输入：iclr格式的json文件

里面每条数据有ltl，ltl_pre，trace字段


### 输出：one-step前缀的json文件

里面每条数据输入字段src: 是由三元组构成的字符串，由公式，路径，可满足性组成

例如 "aUxb, a;{a;&ab},1" 或  "aUxb, $,1" 这里$表示空 

输出字段tgt：是由两个三元组构成的字符串

"aUxb, {a;&ab},1 # a,a;{a;&ab},1"  （表示有两个子节点要证明）
或"aUxb, {a;&ab},1 # @,@,@"  （表示有一个子节点要证明）
或"@,{a;&ab},1 # @,@,@" （表示这个证明节点没有子节点，已经到底了）

The data for LTSatP-ite can be generated using the following command.

```
python3 gen_onestep.py -f train/Finkbeiner-spot-5t20-train.json -o train/LTSatP-ite-spot-5t20-train.json -t 40 -s 800000
```

The test data for LTSatP-ite can be generated using the following command.

```
python3 gen_onestep.py -f train/Finkbeiner-spot-5t20-test.json -o train/LTSatP-ite-spot-5t20-test.json -t 40 -s 100000 --test 1
```


## gen_proof

### 输入：iclr格式的json文件

里面每条数据有ltl，ltl_pre，trace字段

### 输出：tree-proof前缀的json文件

里面每条数据有ltl，ltl_pre，trace字段，还有proof，pair_set字段

proof字段是一个数组，里面每个元素是证明树的（子节点，父节点）对，节点形式是（时刻，（子公式起始下标，子公式结束下标），满足性）

pair_set字段是一个数组，里面第i个元素表示前缀表达式i下标开头的子公式的结束位置

The data for LTSatP can be generated using the following command, which will use 40 threads to convert the first 100K formulae in ```spot/test/spot-5t20-test.json``` and output to ```LTSatP/test/LTSatP-spot-5t20-test.json```.

```
python3 gen_proof.py -f test/Finkbeiner-spot-5t20-test.json -o test/LTSatP-spot-5t20-test.json -t 40 -s 100000
```


## n_gentrace
注意这个py文件同目录下要有temp文件夹,lib文件夹，nuxmv要放在lib里面，且要有运行权限

### 输入：ltl公式文件

每一行为一条ltl公式

### 输出：原始数据集文件

每条数据有：ltl:原始公式，ltl_pre:前缀表达式，trace:使用nuxmv进行生成的路径 或nuxmv_res:表示超时或unsat，ltl_check_res:使用pathchecking对生成路径的检查结果


## splitdata

### 输入：原始数据集文件

就是n_gentrace生成的数据

### 输出：没特殊前缀的例如spot-1t20-train.json

会把原始数据集划分为 正常的：训练集，验证集，测试集

以及超时的，nuxmv认为unsat的，nuxmv和pathchecking结果不一样的

共六个文件

###  splitdata2

多了个步骤：把原始数据集的正常数据里面，被包含在其他测试集的数据给移出，避免训练集混入测试数据


## ltl_model_check的check函数

### 输入：

ltl公式，路径，词汇表

### 输出：

满足/不满足 的判断



## ltl_model_check_proof的check函数

### 输入
ltl公式，路径，词汇表

### 输出

满足性判断，证明树根节点，{父节点：子节点列表}，pair_set，trace(这玩意我咋也输出了？没用的啊)

pair_set字段是一个数组，里面第i个元素表示前缀表达式i下标开头的子公式的结束位置

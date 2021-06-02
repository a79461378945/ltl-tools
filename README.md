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

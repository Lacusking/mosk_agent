# model 模块设计记录

model的调用 和 event 的 设计是紧密相关的
llm的流流式返回的各种状态及工具调用，都需要提前定义好对应的 event

## 实现设计考虑

1、同provider，不同模型的input schema、response、支持的能力都需要不同的处理方法 

2、大体上分为 openai 格式的response、anthropic格式 和其他自定义格式

3、非openai厂商可能也是openai格式，但是也可能有这个厂商自定义的响应或者入参 

4、需要继承整个项目的Base Exception，models包独属的错误，用于在agent runtime层针对不同llm错误响应进行不同的处理

5、同时支持 流式返回和blocking形式输入

6、token在不同阶段消耗，要进行统计

7、对stop reason 和 tool function等要考虑到不同的处理模式

8、要实现event的定义，这两个模块是相辅相成的，需要先考虑会有哪些event会进行传递

## 其他后续实现内容

1、 是否要考虑不同厂商支持 edi_cache,即当需要压缩是，能否对llm厂商的kv cache进行调整，从而减少token消耗

2、retry的实现，虽然有全局的实现，但是目前可能不需要放在这个模块
retry的实现思路为 指数退避 + 随机抖动
0.5^10 + random(0%~25%)ms

3 ...
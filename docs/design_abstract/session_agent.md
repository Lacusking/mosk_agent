# session & agent 模块设计记录

agent 的调用 和 session 的 设计是紧密相关的
同时针对不同agent设计模式单独进行抽象封装，更透彻的理解agent的设计思想

## 实现设计考虑

1、session&agent的状态和schema的定义，状态机如何规划状态迁移

1.1、单轮执行为agent_run,每轮run的产生的多个小步骤为run_step


2、tools 、hooks 、todo｜task、context、memory、policy 可以后续考虑

3、llm正常event处理，异常处理及对应的策略路径需要规划好

4、需要支持流式输出

5、patterns 准备放agent的设计模式的一些策略，比如planing，react、reflection、routing、chaining等

6、agent mode 比如plan / build / review / chat 这些可以作为agent patterns的默认策略（但两者不是绝对的绑定关系，在一定程度上还是两种概念的），但依然可以自主决策合适的场景使用不同的patterns

## 其他后续实现内容

1、 当前为service api调用，可以先不考虑 session 及 agent loop的双层循环嵌套，以特供cli模式运行

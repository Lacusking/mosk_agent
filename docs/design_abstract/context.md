# context 模块设计记录

context是 agent能完成循环的第一步，是agent拥有智能的第一步


## 实现设计考虑

1、 context schema的定义

2、 context 需要考虑token长度 和 llm api windos limit的关系，所以需要考虑到token的计算和重试机制

3、 context的不同策略抽象为不同执行类
3.1、 simple context 单纯将前几轮会话加载到上下文
3.2、 snip compact 剪枝压缩，当轮数过多，导致上下文过长时，保留保留头部关键消息和尾部最近消息，裁掉中间内容
3.3、 micro compact 把大段旧结果替换成占位符或简短摘要


## 其他后续实现内容

1、因为当前尚未实现tool能力，所以对于tool 执行结果的处理后续实现

2、autoCompact当前不实现，后续当 token 超预算且无 LLM 策略无法解决时，调用模型生成 session summary，用 summary 替换部分旧上下文。且尝试了解。llm模型厂商提供的cache 压缩接口的实现
# Bug status

## Bug status 专注于整体Quality Push 中涉及到的 high priority and Edge SLA Bugs。

### Edge SLA Bugs

主要的SLA Bugs 分为三类：
- Blocking bugs
- A11y bugs
- Security bugs

每一种bug，都可以通过配置文件的方法提供一个DAO的Query，可以通过ADO的命令行工具 az来进行获取。
获取以后的数据，需要先进行字段教研，通过校验的数据可以直接保存到Mysql中。

配置文件是通过每一个team 来拥有自己的配置文件。现在已知的team有， Edge Mac Team， Edge Mobile Team 和 Edge Consumer China Team。

### high priority 

同样的规则，大概分为2类：
- Need Triaged
- P0/P1 bugs

每一种bug，都可以通过配置文件的方法提供一个DAO的Query，可以通过ADO的命令行工具 az来进行获取。
获取以后的数据，需要先进行字段教研，通过校验的数据可以直接保存到Mysql中。

配置文件是通过每一个team 来拥有自己的配置文件。现在已知的team有， Edge Mac Team， Edge Mobile Team 和 Edge Consumer China Team。


### bug status 数据展示

数据一共分为5个类别，每个类别在前端展示一张表格。
- Blocking bugs
- A11y bugs
- Security bugs
- Need Triaged
- P0/P1 bugs

数据展示前端部分应该是dashboard 风格。在前端最开始需要展示 数据整体的summary，并且展示最近一个月的趋势变化。 整体风格请参考 edge-mobile_sla_report_2026-02-11.html 这个文件。

后段数据API 使用python 来处理。我建议使用fastapi 来报漏对外的API。